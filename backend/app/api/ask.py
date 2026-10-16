"""Ask a question about your own documents and get a grounded, cited answer (or an honest refusal)."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.answering.service import PASSAGES_FOR_ANSWER, AnswerResult, answer_from_passages
from app.api.documents import get_owned_document
from app.api.subjects import get_owned_subject
from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.llm.base import LLMProvider, ProviderError
from app.llm.providers import build_provider
from app.retrieval.search import search_user_chunks
from app.schemas import AnswerResponse, AskRequest, SourceOut
from app.services.ratelimit import SlidingWindowLimiter

logger = logging.getLogger("studysphere.ask")
router = APIRouter(prefix="/ask", tags=["ask"])


@lru_cache
def _build_provider() -> LLMProvider | None:
    return build_provider(get_settings())


def get_llm_provider() -> LLMProvider | None:
    """A dependency, so tests can swap in a fake provider."""
    try:
        return _build_provider()
    except ProviderError as error:
        logger.error("AI provider is misconfigured: %s", error)
        raise HTTPException(status_code=503, detail="The AI provider is not configured correctly.") from None


@lru_cache
def get_ask_limiter() -> SlidingWindowLimiter:
    return SlidingWindowLimiter(max_events=get_settings().ask_limit_per_hour, window_seconds=3600)


def _to_response(result: AnswerResult) -> AnswerResponse:
    return AnswerResponse(
        status=result.status,
        message=result.message,
        answer=result.answer,
        sources=[
            SourceOut(
                number=number,
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                filename=hit.filename,
                page_number=hit.page_number,
                text=hit.text,
                cited=number in result.cited,
            )
            for number, hit in enumerate(result.passages, start=1)
        ],
        warnings=result.warnings,
        support=result.support,
        provider=result.provider,
    )


@router.post("", response_model=AnswerResponse)
def ask(
    payload: AskRequest,
    db: DbSession,
    current_user: CurrentUser,
    provider: Annotated[LLMProvider | None, Depends(get_llm_provider)],
    limiter: Annotated[SlidingWindowLimiter, Depends(get_ask_limiter)],
) -> AnswerResponse:
    wait = limiter.check(current_user.id)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="You are asking too quickly. Please try again later.",
            headers={"Retry-After": str(wait)},
        )
    if payload.document_id is not None:
        get_owned_document(db, current_user, payload.document_id)  # 404 unless it is yours
    if payload.subject_id is not None:
        get_owned_subject(db, current_user, payload.subject_id)  # 404 unless it is yours

    settings = get_settings()
    _terms, hits = search_user_chunks(
        db, current_user.id, payload.question, payload.document_id, PASSAGES_FOR_ANSWER, payload.subject_id
    )
    result = answer_from_passages(
        payload.question, hits, provider, settings.answer_min_coverage, settings.llm_max_answer_tokens
    )
    # The question text is not logged: it may contain private study content.
    logger.info("User %d asked: status=%s passages=%d", current_user.id, result.status, len(result.passages))
    return _to_response(result)