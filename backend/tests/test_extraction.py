import pytest

from app.services.extraction import (
    ExtractionError,
    UnsupportedFileType,
    clean_filename,
    detect_kind,
    extract_document,
)


def test_clean_filename_drops_folders_and_control_characters():
    assert clean_filename("../../etc/passwd") == "passwd"
    assert clean_filename("C:\\Users\\kzakw\\notes.pdf") == "notes.pdf"
    assert clean_filename("a\x00b\nc.txt") == "abc.txt"
    assert len(clean_filename("a" * 300 + ".pdf")) == 200
    assert clean_filename("a" * 300 + ".pdf").endswith(".pdf")


def test_clean_filename_falls_back_when_empty():
    assert clean_filename(None) == "untitled"
    assert clean_filename("   ") == "untitled"
    assert clean_filename("...") == "untitled"


def test_detect_kind_accepts_pdf_text_and_markdown():
    assert detect_kind("notes.pdf", b"%PDF-1.7 rest") == ("pdf", ".pdf")
    assert detect_kind("NOTES.TXT", b"hello") == ("text", ".txt")
    assert detect_kind("a.md", b"# Title") == ("text", ".md")


def test_detect_kind_rejects_unknown_extensions():
    with pytest.raises(UnsupportedFileType):
        detect_kind("virus.exe", b"MZ")


def test_detect_kind_rejects_a_fake_pdf():
    with pytest.raises(ExtractionError) as info:
        detect_kind("fake.pdf", b"hello")
    assert not isinstance(info.value, UnsupportedFileType)


def test_text_file_is_decoded_and_normalised():
    data = b"\xef\xbb\xbfHello   world\r\n\r\n\r\n\r\nSecond"
    result = extract_document("text", data, max_pages=1, max_chars=1000)
    assert result.page_count == 1
    assert result.pages[0].text == "Hello world\n\nSecond"


def test_binary_masquerading_as_text_is_rejected():
    with pytest.raises(ExtractionError, match="text file"):
        extract_document("text", b"hello\x00world", max_pages=1, max_chars=1000)


def test_invalid_utf8_is_rejected():
    with pytest.raises(ExtractionError, match="UTF-8"):
        extract_document("text", b"caf\xe9", max_pages=1, max_chars=1000)


def test_empty_text_file_is_rejected():
    with pytest.raises(ExtractionError, match="no text"):
        extract_document("text", b"   \n  ", max_pages=1, max_chars=1000)


def test_text_size_limit():
    with pytest.raises(ExtractionError, match="too much text"):
        extract_document("text", b"a " * 600, max_pages=1, max_chars=1000)


def test_pdf_pages_are_extracted_with_page_numbers(make_pdf):
    data = make_pdf(["Binary search halves the search space.", "Linear search checks every item."])
    result = extract_document("pdf", data, max_pages=10, max_chars=100_000)
    assert result.page_count == 2
    assert [page.page_number for page in result.pages] == [1, 2]
    assert "halves" in result.pages[0].text
    assert "Linear" in result.pages[1].text


def test_pdf_without_text_is_rejected(make_pdf):
    with pytest.raises(ExtractionError, match="No text"):
        extract_document("pdf", make_pdf([""]), max_pages=10, max_chars=100_000)


def test_damaged_pdf_is_rejected():
    with pytest.raises(ExtractionError):
        extract_document("pdf", b"%PDF-1.4\nthis is not a real pdf", max_pages=10, max_chars=100_000)


def test_pdf_page_limit(make_pdf):
    with pytest.raises(ExtractionError, match="limit"):
        extract_document("pdf", make_pdf(["one", "two"]), max_pages=1, max_chars=100_000)