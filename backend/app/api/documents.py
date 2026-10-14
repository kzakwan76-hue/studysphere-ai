"""Document upload, listing, reading and deletion. Every query is scoped to the logged-in user."""

import hashlib
import logging

from fastapi import APIRouter, HTTPException, Query, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.models import Chunk, Document, User
from app.schemas import ChunkOut, DocumentOut
from app.services.chunking import chunk_pages
from app.services.extraction import (
    ExtractionError,
    UnsupportedFileType,
    clean_filename,
    detect_kind,
    extract_document,
)
from app.services.storage import delete_upload, save_upload

logger = logging.getLogger("studysphere.documents")
router = APIRouter(prefix="/documents", tags=["documents"])


def get_owned_document(db: Session, user: User, document_id: int) -> Document:
    """The document if it belongs to this user. Missing and someone else's look identical (404)."""
    document = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user.id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(file: UploadFile, db: DbSession, current_user: CurrentUser) -> Document:
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024

    # 1. Size and emptiness: read at most one byte over the limit.
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. The limit is {settings.max_upload_mb} MB.")
    if not data:
        raise HTTPException(status_code=422, detail="The file is empty.")

    # 2. Type: the extension must be allowed and the content must match it.
    filename = clean_filename(file.filename)
    try:
        kind, extension = detect_kind(filename, data)
    except UnsupportedFileType as error:
        raise HTTPException(status_code=415, detail=str(error)) from None
    except ExtractionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None

    # 3. Duplicates and usage limit, checked before the expensive extraction.
    sha256 = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Document).where(Document.user_id == current_user.id, Document.sha256 == sha256))
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"You already uploaded this file as '{existing.filename}'.")
    count = db.scalar(select(func.count(Document.id)).where(Document.user_id == current_user.id)) or 0
    if count >= settings.max_documents_per_user:
        raise HTTPException(
            status_code=403,
            detail=f"Document limit reached ({settings.max_documents_per_user}). Delete a document to upload another.",
        )

    # 4. Extract text and cut it into chunks.
    try:
        extracted = extract_document(kind, data, settings.max_pdf_pages, settings.max_extracted_chars)
    except ExtractionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    chunks = chunk_pages(extracted.pages)

    # 5. Store the file and the database rows. If the database fails, remove the file again.
    storage_path = save_upload(current_user.id, extension, data)
    document = Document(
        user_id=current_user.id,
        filename=filename,
        kind=kind,
        size_bytes=len(data),
        sha256=sha256,
        page_count=extracted.page_count,
        char_count=sum(len(page.text) for page in extracted.pages),
        chunk_count=len(chunks),
        storage_path=storage_path,
    )
    document.chunks = [Chunk(page_number=c.page_number, position=c.position, text=c.text) for c in chunks]
    db.add(document)
    try:
        db.commit()
    except IntegrityError:  # the same file uploaded twice at the same moment
        db.rollback()
        delete_upload(storage_path)
        raise HTTPException(status_code=409, detail="You already uploaded this file.") from None
    except Exception:
        db.rollback()
        delete_upload(storage_path)
        raise
    db.refresh(document)
    logger.info(
        "User %d uploaded document %d (%s, %d pages, %d chunks)",
        current_user.id, document.id, kind, document.page_count, document.chunk_count,
    )
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(db: DbSession, current_user: CurrentUser) -> list[Document]:
    statement = select(Document).where(Document.user_id == current_user.id).order_by(Document.id.desc())
    return list(db.scalars(statement))


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: DbSession, current_user: CurrentUser) -> Document:
    return get_owned_document(db, current_user, document_id)


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def list_chunks(
    document_id: int,
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Chunk]:
    document = get_owned_document(db, current_user, document_id)
    statement = (
        select(Chunk).where(Chunk.document_id == document.id).order_by(Chunk.position).limit(limit).offset(offset)
    )
    return list(db.scalars(statement))


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: DbSession, current_user: CurrentUser) -> Response:
    document = get_owned_document(db, current_user, document_id)
    storage_path = document.storage_path
    db.delete(document)  # the database removes the chunks (ON DELETE CASCADE)
    db.commit()
    delete_upload(storage_path)
    logger.info("User %d deleted document %d", current_user.id, document_id)
    return Response(status_code=204)