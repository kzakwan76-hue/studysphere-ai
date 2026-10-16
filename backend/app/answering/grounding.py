"""Checks on the model's answer: are its citations real, and does it stick to the cited passages?"""

import re
from dataclasses import dataclass

from app.retrieval.tokenizer import tokenize

CITATION = re.compile(r"\[(\d{1,3})\]")
LOW_SUPPORT = 0.5  # below this share of answer words found in the cited passages, a warning is shown


@dataclass(frozen=True)
class CitationCheck:
    valid: bool
    cited: frozenset[int]
    problem: str | None


def verify_citations(answer: str, passage_count: int) -> CitationCheck:
    """An answer is only accepted if it cites at least one passage and every citation exists."""
    numbers = [int(match) for match in CITATION.findall(answer)]
    if not numbers:
        return CitationCheck(False, frozenset(), "The answer cited no sources.")
    missing = sorted({number for number in numbers if not 1 <= number <= passage_count})
    if missing:
        return CitationCheck(False, frozenset(), f"The answer cited sources that do not exist: {missing}.")
    return CitationCheck(True, frozenset(numbers), None)


def uncited_sentences(answer: str) -> list[str]:
    """Sentences without a citation. A citation placed after the full stop still counts."""
    sentences = re.split(r"(?<=[.!?])\s+(?!\[)", answer.strip())
    return [sentence for sentence in sentences if sentence and not CITATION.search(sentence)]


def support_score(answer: str, cited_texts: list[str]) -> float:
    """Heuristic: the share of the answer's content words that also appear in the cited passages.

    It cannot prove an answer is correct. A low score is a hint that the answer goes beyond the sources.
    """
    answer_terms = set(tokenize(CITATION.sub(" ", answer)))
    if not answer_terms:
        return 0.0
    source_terms = {term for text in cited_texts for term in tokenize(text)}
    return len(answer_terms & source_terms) / len(answer_terms)