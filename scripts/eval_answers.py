"""Measure the whole answering pipeline on the synthetic documents. No server or database needed.

Run from the project root:  python scripts\\eval_answers.py [question_file.json]

Uses the provider set in .env (LLM_PROVIDER). With "none" it can only show which questions pass the
relevance gate. With "ollama" or "anthropic" it measures real answers.

Besides the totals it explains every failure: was the expected passage retrieved, did the relevance
gate refuse, or did the model refuse? It also shows how the gate would behave at other thresholds.
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

THRESHOLDS = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)


def squash(text: str) -> str:
    return " ".join(text.lower().split())


def is_expected(hit: SearchHit, expected_file: str, evidence: str | None) -> bool:
    """True when this passage is from the expected file and contains the expected evidence text."""
    return hit.filename == expected_file and squash(evidence or "") in squash(hit.text)


def shorten(text: str, limit: int = 70) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


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
    refusal_reasons: Counter[str] = Counter()  # why answerable questions were refused: "gate" or "model"
    refused_but_retrieved = 0
    correct = 0
    problems: list[str] = []
    answerable_coverage: list[float] = []
    unanswerable_coverage: list[float] = []

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
        best = max((hit.coverage for hit in hits), default=0.0)
        gate_open = bool(hits) and best >= settings.answer_min_coverage
        result = answer_from_passages(
            item.question, hits, provider, settings.answer_min_coverage, settings.llm_max_answer_tokens
        )
        question = shorten(item.question)

        if item.expected_file is None:
            unanswerable[result.status] += 1
            unanswerable_coverage.append(best)
            if result.status in ("answered", "passages_only"):
                problems.append(f"NOT IN DOCS BUT {result.status.upper():<8} coverage={best:.2f}  {question}")
            continue

        answerable[result.status] += 1
        answerable_coverage.append(best)
        retrieved = any(is_expected(hit, item.expected_file, item.evidence) for hit in hits)
        retrieved_text = "yes" if retrieved else "no"
        if result.status == "not_found":
            reason = "gate" if not gate_open else "model"
            refusal_reasons[reason] += 1
            refused_but_retrieved += int(retrieved)
            problems.append(
                f"FALSE REFUSAL by {reason:<5} coverage={best:.2f} expected passage retrieved={retrieved_text}  {question}"
            )
        elif result.status == "answered":
            cited = [result.passages[number - 1] for number in result.cited]
            if any(is_expected(hit, item.expected_file, item.evidence) for hit in cited):
                correct += 1
            else:
                problems.append(
                    f"WRONG CITATION      coverage={best:.2f} expected passage retrieved={retrieved_text}  {question}"
                )
        elif result.status != "passages_only":
            problems.append(f"{result.status.upper():<19} coverage={best:.2f}  {question}")

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

    refused = answerable["not_found"]
    if refused:
        print("\nWhy the false refusals happened")
        print(f"  Relevance gate closed (model never called): {refusal_reasons['gate']}/{refused}")
        print(f"  Model replied INSUFFICIENT_INFORMATION:     {refusal_reasons['model']}/{refused}")
        print(f"  Expected passage was among those retrieved: {refused_but_retrieved}/{refused}")

    if problems:
        print("\nEvery problem case:")
        for line in problems:
            print("  " + line)

    print("\nGate-only sweep (no model involved): how many questions would pass the gate")
    print("  threshold  answerable  unanswerable")
    for threshold in THRESHOLDS:
        passing_answerable = sum(value >= threshold for value in answerable_coverage)
        passing_unanswerable = sum(value >= threshold for value in unanswerable_coverage)
        print(
            f"  {threshold:<9.1f}  {passing_answerable:>2}/{len(answerable_coverage):<7}"
            f"  {passing_unanswerable:>2}/{len(unanswerable_coverage)}"
        )
    print("  You want answerable high and unanswerable low. Passing the gate does not mean the right passage was found.")


if __name__ == "__main__":
    main()