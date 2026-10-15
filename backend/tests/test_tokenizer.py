from app.retrieval.tokenizer import stem, tokenize


def test_lowercases_splits_on_punctuation_and_stems():
    assert tokenize("Binary-search, halves!") == ["binary", "search", "halve"]


def test_filler_words_are_removed():
    assert tokenize("What is the time complexity of the search?") == ["time", "complexity", "search"]


def test_stemmer_examples():
    assert stem("searches") == stem("searching") == stem("searched") == "search"
    assert stem("classes") == "class" and stem("class") == "class"
    assert stem("queries") == "query"
    assert stem("hashes") == "hash"
    assert stem("items") == "item"
    assert stem("string") == "string" and stem("strings") == "string"  # 'string' must not become 'str'
    assert stem("analysis") == "analysis"
    assert stem("bus") == "bus" and stem("speed") == "speed"


def test_non_english_letters_are_kept():
    assert tokenize("Café résumé") == ["café", "résumé"]


def test_digits_are_kept_and_single_letters_dropped():
    assert tokenize("log2 of 1000000") == ["log2", "1000000"]
    assert tokenize("a b c") == []