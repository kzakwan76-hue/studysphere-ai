"""Turn retrieved passages into a grounded, verified answer, or an honest refusal."""

import logging
from dataclasses import dataclass, field

from app.answering.grounding import LOW_SUPPORT, support_score, uncited_sentences, verify_citations
from app.answering.prompt import INSUFFICIENT, SYSTEM_PROMPT, build_user_prompt
from app.llm.base import LLMProvider, ProviderError
from app.retrieval.search import SearchHit

logger = logging.getLogger("studysphere.answering")

PASSAGES_FOR_ANSWER = 5

NOT_FOUND_MESSAGE = (
    "I couldn't find this in your documents, so I won't guess. Try rephrasing, or upload notes that cover it."
)
NO_MODEL_MESSAGE = "No AI model is configured, so here are the most relevant passages from your documents."
UNAVAILABLE_MESSAGE = "The AI model could not be reached, so here are the most relevant passages from your documents."
UNVERIFIED_MESSAGE = (
    "The AI's answer could not be verified against your documents, so it was withheld. "
    "Here are the most relevant passages."
)


@dataclass(frozen=True)
class AnswerResult:
    status: str  # answered | passages_only | not_found | unverified | unavailable
    message: str
    answer: str | None = None
    passages: list[SearchHit] = field(default_factory=list)  # numbered 1..n in the order shown
    cited: frozenset[int] = frozenset()  # numbers of the passages the answer cites
    support: float | None = None
    warnings: list[str] = field(default_factory=list)
    provider: str | None = None


def answer_from_passages(
    question: str,
    hits: list[SearchHit],
    provider: LLMProvider | None,
    min_coverage: float,
    max_tokens: int,
) -> AnswerResult:
    """Decide what to tell the student. The model is only called when the passages look relevant."""
    if not hits or max(hit.coverage for hit in hits) < min_coverage:
        return AnswerResult("not_found", NOT_FOUND_MESSAGE)
    if provider is None:
        return AnswerResult("passages_only", NO_MODEL_MESSAGE, passages=hits)

    try:
        reply = provider.generate(SYSTEM_PROMPT, build_user_prompt(question, hits), max_tokens)
    except ProviderError as error:
        logger.warning("AI provider failed: %s", error)
        return AnswerResult("unavailable", UNAVAILABLE_MESSAGE, passages=hits, provider=provider.name)

    if INSUFFICIENT in reply:
        return AnswerResult("not_found", NOT_FOUND_MESSAGE, provider=provider.name)

    check = verify_citations(reply, len(hits))
    if not check.valid:
        logger.warning("AI answer withheld: %s", check.problem)
        return AnswerResult(
            "unverified",
            UNVERIFIED_MESSAGE,
            passages=hits,
            warnings=[check.problem] if check.problem else [],
            provider=provider.name,
        )

    support = support_score(reply, [hits[number - 1].text for number in sorted(check.cited)])
    warnings: list[str] = []
    if uncited_sentences(reply):
        warnings.append("Some sentences in this answer have no citation.")
    if support < LOW_SUPPORT:
        warnings.append("Parts of this answer use words that do not appear in the cited passages. Check the sources.")
    return AnswerResult(
        "answered",
        "Answer based on your documents.",
        answer=reply.strip(),
        passages=hits,
        cited=check.cited,
        support=round(support, 2),
        warnings=warnings,
        provider=provider.name,
    )