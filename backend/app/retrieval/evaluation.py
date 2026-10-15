"""Measure how well retrieval finds the right passage, using synthetic documents with known answers."""

import json
from dataclasses import dataclass
from pathlib import Path

from app.retrieval.ranking import rank_passages
from app.services.chunking import chunk_pages
from app.services.extraction import extract_document

DEFAULT_KS = (1, 3, 5)


@dataclass(frozen=True)
class CorpusChunk:
    filename: str
    page_number: int
    text: str


@dataclass(frozen=True)
class Question:
    question: str
    expected_file: str | None  # None means the question cannot be answered from the documents
    evidence: str | None  # a phrase that must appear in the passage that answers it


@dataclass(frozen=True)
class RetrievalReport:
    answerable: int
    unanswerable: int
    hit_at: dict[int, float]  # k -> share of answerable questions with the right passage in the top k
    mrr: float  # mean reciprocal rank: 1 if the right passage is first, 1/2 if second, and so on
    misses: list[str]  # answerable questions whose right passage was not in the top results
    top_coverage_answerable: list[float]
    unanswerable_questions: list[str]
    top_coverage_unanswerable: list[float]


def load_corpus(folder: Path) -> list[CorpusChunk]:
    """Chunk every .md and .txt file with the same code the app uses for uploads."""
    corpus: list[CorpusChunk] = []
    for path in sorted(folder.glob("*.md")) + sorted(folder.glob("*.txt")):
        extracted = extract_document("text", path.read_bytes(), max_pages=1, max_chars=2_000_000)
        corpus.extend(CorpusChunk(path.name, chunk.page_number, chunk.text) for chunk in chunk_pages(extracted.pages))
    return corpus


def load_questions(path: Path) -> list[Question]:
    items = json.loads(path.read_text(encoding="utf-8"))
    return [Question(item["question"], item["file"], item["evidence"]) for item in items]


def _squash(text: str) -> str:
    return " ".join(text.lower().split())


def _is_correct(chunk: CorpusChunk, question: Question) -> bool:
    return chunk.filename == question.expected_file and _squash(question.evidence or "") in _squash(chunk.text)


def evaluate(questions: list[Question], corpus: list[CorpusChunk], ks: tuple[int, ...] = DEFAULT_KS) -> RetrievalReport:
    texts = [chunk.text for chunk in corpus]
    deepest = max(ks)
    hits = {k: 0 for k in ks}
    reciprocal_ranks: list[float] = []
    misses: list[str] = []
    answerable_coverage: list[float] = []
    unanswerable_questions: list[str] = []
    unanswerable_coverage: list[float] = []
    answerable = 0

    for item in questions:
        _terms, ranked = rank_passages(item.question, texts, limit=deepest)
        top_coverage = ranked[0].coverage if ranked else 0.0

        if item.expected_file is None:
            unanswerable_questions.append(item.question)
            unanswerable_coverage.append(top_coverage)
            continue

        answerable += 1
        answerable_coverage.append(top_coverage)
        rank = next(
            (
                position
                for position, passage in enumerate(ranked, start=1)
                if _is_correct(corpus[passage.index], item)
            ),
            None,
        )
        if rank is None:
            misses.append(item.question)
            continue
        reciprocal_ranks.append(1 / rank)
        for k in ks:
            if rank <= k:
                hits[k] += 1

    if answerable == 0:
        raise ValueError("The question set has no answerable questions.")
    return RetrievalReport(
        answerable=answerable,
        unanswerable=len(unanswerable_questions),
        hit_at={k: hits[k] / answerable for k in ks},
        mrr=sum(reciprocal_ranks) / answerable,
        misses=misses,
        top_coverage_answerable=answerable_coverage,
        unanswerable_questions=unanswerable_questions,
        top_coverage_unanswerable=unanswerable_coverage,
    )