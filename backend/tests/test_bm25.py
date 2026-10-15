from app.retrieval.bm25 import BM25Index


def test_only_documents_containing_the_term_are_returned():
    index = BM25Index([["cat", "dog"], ["dog", "bird"], ["fish"]])
    assert [hit.index for hit in index.search(["dog"])] == [0, 1]
    assert [hit.index for hit in index.search(["fish"])] == [2]


def test_rare_terms_outweigh_common_terms():
    index = BM25Index([["common", "rare"], ["common", "other"], ["common", "x"]])
    hits = index.search(["common", "rare"])
    assert hits[0].index == 0
    assert hits[0].score > hits[1].score


def test_repeated_terms_help_but_with_diminishing_returns():
    index = BM25Index([["apple"] + ["f"] * 9, ["apple"] * 2 + ["f"] * 8, ["apple"] * 4 + ["f"] * 6])
    score = {hit.index: hit.score for hit in index.search(["apple"])}
    assert score[0] < score[1] < score[2]
    assert (score[1] - score[0]) > (score[2] - score[1]) / 2  # the second repeat adds more than the later ones


def test_shorter_documents_win_when_counts_are_equal():
    index = BM25Index([["apple", "x"], ["apple"] + ["y"] * 20, ["zzz"] * 10])
    assert index.search(["apple"])[0].index == 0


def test_empty_index_and_unknown_terms():
    assert BM25Index([]).search(["anything"]) == []
    assert BM25Index([["a1", "b1"]]).search(["zzz"]) == []


def test_ties_are_broken_by_position():
    index = BM25Index([["same", "words"], ["same", "words"]])
    assert [hit.index for hit in index.search(["same"])] == [0, 1]


def test_limit_is_respected():
    index = BM25Index([["apple"]] * 5)
    assert len(index.search(["apple"], limit=2)) == 2