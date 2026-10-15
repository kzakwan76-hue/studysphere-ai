import pytest

from app.retrieval.ranking import rank_passages

TEXTS = [
    "Binary search halves the list each step.",
    "A hash table maps keys to buckets.",
    "Bananas are yellow.",
]


def test_finds_the_passage_and_reports_coverage():
    terms, ranked = rank_passages("How does binary search work?", TEXTS)
    assert terms == ["binary", "search", "work"]
    assert len(ranked) == 1 and ranked[0].index == 0
    assert ranked[0].matched_terms == ["binary", "search"]
    assert ranked[0].coverage == pytest.approx(2 / 3)


def test_a_question_made_only_of_filler_words_searches_nothing():
    assert rank_passages("what is the", TEXTS) == ([], [])


def test_no_match_gives_no_passages():
    terms, ranked = rank_passages("quantum entanglement", TEXTS)
    assert terms == ["quantum", "entanglement"]
    assert ranked == []


def test_limit_is_respected():
    _terms, ranked = rank_passages("apple pie", ["apple pie"] * 5, limit=3)
    assert len(ranked) == 3


def test_plural_in_the_question_matches_singular_in_the_text():
    _terms, ranked = rank_passages("algorithms", ["Algorithm choice matters", "unrelated words"])
    assert ranked[0].index == 0