"""Measure the whole answering pipeline on the synthetic documents. No server or database needed.

Run from the project root:  python scripts\\eval_answers.py [question_file.json]

Uses the provider set in .env (LLM_PROVIDER). With "none" it can only show which questions pass the
relevance gate. With "ollama" or "anthropic" it measures real answers.
"""

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.answering.service import PASSAGES_FOR_ANSWER, answer_from_passages  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.llm.providers import build_provider  # noqa: E402
from app.retrieval.evaluation import load_corpus, load_questions  # noqa: E402
from app.retrieval.ranking import rank_passages  # noqa: E402
from app.retrieval.search import SearchHit  # noqa: E402


def squash(text: str) -> str:
    return " ".join(text.lower().split())


def main() -> None:
    settings = get_settings()
    provider = build_provider(settings)
    corpus = load_corpus(ROOT / "sample_docs")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "eval" / "retrieval_questions.json"
    questions = load_questions(path)
    texts = [chunk.text for chunk in corpus]
    print(
        f"Provider: {provider.name if provider else 'none'} | question set: {path.name} | "
        f"min coverage: {settings.answer_min_coverage}\n"
    )

    answerable: Counter[str] = Counter()
    unanswerable: Counter[str] = Counter()
    correct = 0
    for item in questions:
        _terms, ranked = rank_passages(item.question, texts, limit=PASSAGES_FOR_ANSWER)
        hits = [
            SearchHit(
                chunk_id=passage.index, document_id=0,
                filename=corpus[passage.index].filename, page_number=corpus[passage.index].page_number,
                score=passage.score, coverage=passage.coverage, matched_terms=passage.matched_terms,
                text=corpus[passage.index].text,
            )
            for passage in ranked
        ]
        result = answer_from_passages(
            item.question, hits, provider, settings.answer_min_coverage, settings.llm_max_answer_tokens
        )
        if item.expected_file is None:
            unanswerable[result.status] += 1
            continue
        answerable[result.status] += 1
        if result.status == "answered":
            cited = [result.passages[number - 1] for number in result.cited]
            if any(
                hit.filename == item.expected_file and squash(item.evidence or "") in squash(hit.text)
                for hit in cited
            ):
                correct += 1

    total_answerable = sum(answerable.values())
    total_unanswerable = sum(unanswerable.values())
    print(f"Answerable questions ({total_answerable}): {dict(answerable)}")
    print(f"Unanswerable questions ({total_unanswerable}): {dict(unanswerable)}\n")
    print(f"Answerable but refused (false refusals): {answerable['not_found']}/{total_answerable}")
    print(f"Unanswerable and refused (correct):      {unanswerable['not_found']}/{total_unanswerable}")
    if provider is None:
        print("\nNo AI provider configured: set LLM_PROVIDER in .env to measure real answers.")
        print("'passages_only' means the question passed the relevance gate.")
    else:
        print(f"Answered with the right passage cited:   {correct}/{total_answerable}")
        print(f"Unanswerable but answered anyway:        {unanswerable['answered']}/{total_unanswerable}")


if __name__ == "__main__":
    main()