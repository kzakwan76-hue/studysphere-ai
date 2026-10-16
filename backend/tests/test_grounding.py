import pytest

from app.answering.grounding import support_score, uncited_sentences, verify_citations


def test_valid_citations_are_collected():
    check = verify_citations("Binary search halves the list [1]. It needs sorting [2][1].", passage_count=3)
    assert check.valid and check.cited == frozenset({1, 2}) and check.problem is None


def test_an_answer_without_citations_is_invalid():
    assert not verify_citations("Binary search halves the list.", 3).valid


@pytest.mark.parametrize("answer", ["Fact [4].", "Fact [0].", "Fact [1] and [9]."])
def test_citations_to_missing_passages_are_invalid(answer):
    check = verify_citations(answer, passage_count=3)
    assert not check.valid and "do not exist" in check.problem


def test_uncited_sentences_are_found():
    assert uncited_sentences("One [1]. Two. Three [2].") == ["Two."]
    assert uncited_sentences("One. [1] Two [2].") == []
    assert uncited_sentences("One [1]. Two [2].") == []


def test_support_is_high_when_the_answer_uses_the_passage_words():
    passage = "Binary search halves the sorted list at every step."
    assert support_score("Binary search halves the sorted list [1].", [passage]) == pytest.approx(1.0)


def test_support_is_low_when_the_answer_goes_beyond_the_passage():
    passage = "Binary search halves the sorted list at every step."
    assert support_score("Quantum gluons bind quarks together [1].", [passage]) == 0.0


def test_an_answer_with_no_words_has_no_support():
    assert support_score("[1]", ["anything"]) == 0.0