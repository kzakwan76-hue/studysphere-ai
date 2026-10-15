from pathlib import Path

from app.retrieval.evaluation import CorpusChunk, Question, evaluate, load_corpus, load_questions

ROOT = Path(__file__).resolve().parents[2]


def test_metrics_on_a_tiny_corpus():
    corpus = [
        CorpusChunk("a.md", 1, "Binary search halves a sorted list."),
        CorpusChunk("b.md", 1, "Photosynthesis happens in chloroplasts."),
    ]
    questions = [
        Question("How does binary search work?", "a.md", "halves a sorted list"),
        Question("Where does photosynthesis happen?", "b.md", "in chloroplasts"),
        Question("Who won the football World Cup?", None, None),
    ]
    report = evaluate(questions, corpus)
    assert (report.answerable, report.unanswerable) == (2, 1)
    assert report.hit_at == {1: 1.0, 3: 1.0, 5: 1.0}
    assert report.mrr == 1.0
    assert report.misses == []
    assert report.top_coverage_unanswerable == [0.0]


def test_a_wrong_answer_counts_as_a_miss():
    corpus = [CorpusChunk("a.md", 1, "Binary search halves a sorted list.")]
    report = evaluate([Question("How does binary search work?", "a.md", "something not in the text")], corpus)
    assert report.hit_at[5] == 0.0 and report.mrr == 0.0
    assert report.misses == ["How does binary search work?"]


def test_synthetic_corpus_loads_and_retrieval_is_not_broken():
    corpus = load_corpus(ROOT / "sample_docs")
    questions = load_questions(ROOT / "eval" / "retrieval_questions.json")
    report = evaluate(questions, corpus)
    assert len({chunk.filename for chunk in corpus}) >= 5
    assert report.answerable >= 15 and report.unanswerable >= 5
    assert report.hit_at[5] >= 0.5  # a loose floor that catches a broken pipeline; it is not a quality target