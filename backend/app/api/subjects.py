"""Subjects: named groups of your documents, plus the dashboard. Every query is scoped to the logged-in user."""

import logging

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.documents import get_owned_document
from app.deps import CurrentUser, DbSession
from app.models import Document, Subject, SubjectDocument, User
from app.schemas import DashboardOut, DocumentOut, DocumentSummary, SubjectCreate, SubjectOut

logger = logging.getLogger("studysphere.subjects")
router = APIRouter(tags=["subjects"])

MAX_SUBJECTS_PER_USER = 30


def get_owned_subject(db: Session, user: User, subject_id: int) -> Subject:
    """The subject if it belongs to this user. Missing and someone else's look identical (404)."""
    subject = db.scalar(select(Subject).where(Subject.id == subject_id, Subject.user_id == user.id))
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found.")
    return subject


def _subjects_with_counts(db: Session, user_id: int) -> list[SubjectOut]:
    statement = (
        select(Subject, func.count(Document.id), func.coalesce(func.sum(Document.chunk_count), 0))
        .outerjoin(SubjectDocument, SubjectDocument.subject_id == Subject.id)
        .outerjoin(Document, Document.id == SubjectDocument.document_id)
        .where(Subject.user_id == user_id)
        .group_by(Subject.id)
        .order_by(Subject.name)
    )
    return [
        SubjectOut(
            id=subject.id,
            name=subject.name,
            document_count=int(documents),
            chunk_count=int(chunks),
            created_at=subject.created_at,
        )
        for subject, documents, chunks in db.execute(statement).all()
    ]


@router.post("/subjects", response_model=SubjectOut, status_code=201)
def create_subject(payload: SubjectCreate, db: DbSession, current_user: CurrentUser) -> SubjectOut:
    count = db.scalar(select(func.count(Subject.id)).where(Subject.user_id == current_user.id)) or 0
    if count >= MAX_SUBJECTS_PER_USER:
        raise HTTPException(
            status_code=403, detail=f"Subject limit reached ({MAX_SUBJECTS_PER_USER}). Delete a subject first."
        )
    duplicate = db.scalar(
        select(Subject.id).where(Subject.user_id == current_user.id, func.lower(Subject.name) == payload.name.lower())
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="You already have a subject with this name.")
    subject = Subject(user_id=current_user.id, name=payload.name)
    db.add(subject)
    try:
        db.commit()
    except IntegrityError:  # the same name created twice at the same moment
        db.rollback()
        raise HTTPException(status_code=409, detail="You already have a subject with this name.") from None
    db.refresh(subject)
    logger.info("User %d created subject %d", current_user.id, subject.id)
    return SubjectOut(
        id=subject.id, name=subject.name, document_count=0, chunk_count=0, created_at=subject.created_at
    )


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: DbSession, current_user: CurrentUser) -> list[SubjectOut]:
    return _subjects_with_counts(db, current_user.id)


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: int, db: DbSession, current_user: CurrentUser) -> Response:
    """Deletes the subject only. Its documents stay in your library."""
    subject = get_owned_subject(db, current_user, subject_id)
    db.execute(delete(SubjectDocument).where(SubjectDocument.subject_id == subject.id))
    db.delete(subject)
    db.commit()
    logger.info("User %d deleted subject %d", current_user.id, subject_id)
    return Response(status_code=204)


@router.get("/subjects/{subject_id}/documents", response_model=list[DocumentOut])
def list_subject_documents(subject_id: int, db: DbSession, current_user: CurrentUser) -> list[Document]:
    subject = get_owned_subject(db, current_user, subject_id)
    statement = (
        select(Document)
        .join(SubjectDocument, SubjectDocument.document_id == Document.id)
        .where(SubjectDocument.subject_id == subject.id, Document.user_id == current_user.id)
        .order_by(Document.id.desc())
    )
    return list(db.scalars(statement))


@router.put("/subjects/{subject_id}/documents/{document_id}", status_code=204)
def add_document_to_subject(subject_id: int, document_id: int, db: DbSession, current_user: CurrentUser) -> Response:
    """Puts one of your documents in one of your subjects. If it was in another subject, it moves."""
    subject = get_owned_subject(db, current_user, subject_id)
    document = get_owned_document(db, current_user, document_id)
    link = db.get(SubjectDocument, document.id)
    if link is None:
        db.add(SubjectDocument(document_id=document.id, subject_id=subject.id))
    else:
        link.subject_id = subject.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Please try again.") from None
    return Response(status_code=204)


@router.delete("/subjects/{subject_id}/documents/{document_id}", status_code=204)
def remove_document_from_subject(
    subject_id: int, document_id: int, db: DbSession, current_user: CurrentUser
) -> Response:
    subject = get_owned_subject(db, current_user, subject_id)
    document = get_owned_document(db, current_user, document_id)
    db.execute(
        delete(SubjectDocument).where(
            SubjectDocument.subject_id == subject.id, SubjectDocument.document_id == document.id
        )
    )
    db.commit()
    return Response(status_code=204)


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DbSession, current_user: CurrentUser) -> DashboardOut:
    rows = db.execute(
        select(Document, SubjectDocument.subject_id)
        .outerjoin(SubjectDocument, SubjectDocument.document_id == Document.id)
        .where(Document.user_id == current_user.id)
        .order_by(Document.id.desc())
    ).all()
    documents = [
        DocumentSummary(
            id=document.id,
            filename=document.filename,
            kind=document.kind,
            size_bytes=document.size_bytes,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            subject_id=subject_id,
            created_at=document.created_at,
        )
        for document, subject_id in rows
    ]
    return DashboardOut(
        document_count=len(documents),
        chunk_count=sum(document.chunk_count for document in documents),
        unassigned_document_count=sum(1 for document in documents if document.subject_id is None),
        subjects=_subjects_with_counts(db, current_user.id),
        documents=documents,
    )