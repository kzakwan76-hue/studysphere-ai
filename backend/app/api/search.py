"""Search across the logged-in user's documents."""

import logging
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.documents import get_owned_document
from app.deps import CurrentUser, DbSession
from app.retrieval.search import search_user_chunks
from app.schemas import SearchHitOut, SearchResponse

logger = logging.getLogger("studysphere.search")
router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    db: DbSession,
    current_user: CurrentUser,
    q: Annotated[str, Query(min_length=2, max_length=300)],
    document_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> SearchResponse:
    """Find the passages that best match a question. Only your own documents are searched."""
    if document_id is not None:
        get_owned_document(db, current_user, document_id)  # 404 unless it is yours
    terms, hits = search_user_chunks(db, current_user.id, q, document_id, limit)
    # The query text itself is not logged: it may contain private study content.
    logger.info("User %d searched: %d terms, %d results", current_user.id, len(terms), len(hits))
    return SearchResponse(
        query=q,
        terms=terms,
        results=[SearchHitOut.model_validate(hit, from_attributes=True) for hit in hits],
    )