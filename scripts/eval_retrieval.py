"""Measure retrieval quality on the synthetic documents. No server or database needed.

Run from the project root:  python scripts\\eval_retrieval.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.retrieval.evaluation import evaluate, load_corpus, load_questions  # noqa: E402

THRESHOLDS = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0)


def share_at_least(values: list[float], threshold: float) -> float:
    return sum(value >= threshold - 1e-9 for value in values) / len(values) if values else 0.0


def main() -> None:
    corpus = load_corpus(ROOT / "sample_docs")
    questions = load_questions(ROOT / "eval" / "retrieval_questions.json")
    report = evaluate(questions, corpus)

    print(f"Corpus: {len({chunk.filename for chunk in corpus})} documents, {len(corpus)} chunks")
    print(f"Questions: {report.answerable} answerable, {report.unanswerable} unanswerable\n")

    print("Was the right passage among the top k results? (answerable questions)")
    for k, value in report.hit_at.items():
        print(f"  hit@{k}: {value:.2f}")
    print(f"  MRR:   {report.mrr:.2f}\n")

    if report.misses:
        print("Right passage NOT found in the top results for:")
        for question in report.misses:
            print(f"  - {question}")
        print()

    print("Coverage = share of the question's key words found in the top result.")
    print("Could a 'relevant enough' threshold on coverage separate answerable from unanswerable questions?\n")
    print(f"{'threshold':>10}  {'answerable kept':>16}  {'unanswerable wrongly kept':>26}")
    for threshold in THRESHOLDS:
        kept = share_at_least(report.top_coverage_answerable, threshold)
        wrong = share_at_least(report.top_coverage_unanswerable, threshold)
        print(f"{threshold:>10.1f}  {kept:>16.2f}  {wrong:>26.2f}")

    print("\nBest coverage found for each unanswerable question:")
    ranked = sorted(zip(report.unanswerable_questions, report.top_coverage_unanswerable), key=lambda pair: -pair[1])
    for question, coverage in ranked:
        print(f"  {coverage:.2f}  {question}")


if __name__ == "__main__":
    main()