from app.services.chunking import PageText, chunk_pages, chunk_text, normalize_text


def test_normalize_collapses_whitespace_and_drops_nul_bytes():
    messy = "  Hello \t world \r\n\r\n\r\n\r\n next\x00 line  "
    assert normalize_text(messy) == "Hello world\n\nnext line"


def test_empty_text_gives_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_is_one_chunk():
    assert chunk_text("A short note.") == ["A short note."]


def test_long_text_is_split_into_chunks_within_the_limit():
    text = " ".join(f"word{number}" for number in range(1000))
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all(len(chunk) <= 800 for chunk in chunks)


def test_consecutive_chunks_overlap_and_nothing_is_lost():
    words = [f"w{number}" for number in range(1000)]
    chunks = chunk_text(" ".join(words))
    assert {word for chunk in chunks for word in chunk.split()} == set(words)
    for before, after in zip(chunks, chunks[1:]):
        assert before.split()[-1] in after.split()


def test_paragraph_boundary_is_preferred():
    first = " ".join(["alpha"] * 80)
    second = " ".join(["omega"] * 80)
    chunks = chunk_text(first + "\n\n" + second)
    assert len(chunks) == 2
    assert chunks[0] == first
    assert "omega" in chunks[1]


def test_text_without_spaces_still_terminates():
    chunks = chunk_text("a" * 5000)
    assert len(chunks) == 7
    assert all(len(chunk) <= 800 for chunk in chunks)


def test_chunk_pages_keeps_page_numbers_and_positions():
    pages = [PageText(1, "short one"), PageText(3, "x " * 500)]
    chunks = chunk_pages(pages)
    assert chunks[0].page_number == 1 and chunks[0].text == "short one"
    assert {chunk.page_number for chunk in chunks} == {1, 3}
    assert [chunk.position for chunk in chunks] == list(range(len(chunks)))