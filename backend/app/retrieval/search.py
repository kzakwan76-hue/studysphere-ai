"""Searching one user's own document chunks."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Document, SubjectDocument
from app.retrieval.ranking import rank_passages


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    document_id: int
    filename: str
    page_number: int
    score: float
    coverage: float
    matched_terms: list[str]
    text: str


def search_user_chunks(
    db: Session,
    user_id: int,
    query: str,
    document_id: int | None = None,
    limit: int = 5,
    subject_id: int | None = None,
) -> tuple[list[str], list[SearchHit]]:
    """Rank the passages of this user's documents. The index is rebuilt per search (fine for study notes)."""
    statement = (
        select(Chunk, Document.filename)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.user_id == user_id)
        .order_by(Chunk.id)
    )
    if document_id is not None:
        statement = statement.where(Document.id == document_id)
    if subject_id is not None:
        statement = statement.join(SubjectDocument, SubjectDocument.document_id == Document.id).where(
            SubjectDocument.subject_id == subject_id
        )
    rows = db.execute(statement).all()

    terms, ranked = rank_passages(query, [chunk.text for chunk, _filename in rows], limit)
    hits: list[SearchHit] = []
    for passage in ranked:
        chunk, filename = rows[passage.index]
        hits.append(
            SearchHit(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=filename,
                page_number=chunk.page_number,
                score=passage.score,
                coverage=passage.coverage,
                matched_terms=passage.matched_terms,
                text=chunk.text,
            )
        )
    return terms, hits