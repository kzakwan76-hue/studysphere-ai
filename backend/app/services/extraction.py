"""Turn uploaded files into text, page by page. Uploaded files are untrusted input."""

import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath

from pypdf import PdfReader

from app.services.chunking import PageText, normalize_text

logger = logging.getLogger("studysphere.extraction")

ALLOWED_EXTENSIONS = {".pdf": "pdf", ".txt": "text", ".md": "text"}


class ExtractionError(Exception):
    """The file cannot be turned into text. The message is safe to show to the user."""


class UnsupportedFileType(ExtractionError):
    """The file extension is not one we accept."""


@dataclass(frozen=True)
class ExtractedDocument:
    page_count: int
    pages: list[PageText]  # only pages that contain text


def clean_filename(raw: str | None) -> str:
    """Keep only the final path component, drop control characters, and cap the length."""
    name = (raw or "").replace("\\", "/").split("/")[-1]
    name = "".join(character for character in name if character.isprintable()).strip().strip(".")
    if len(name) > 200:
        suffix = PurePath(name).suffix[:16]
        name = name[: 200 - len(suffix)] + suffix
    return name or "untitled"


def detect_kind(filename: str, data: bytes) -> tuple[str, str]:
    """Return (kind, extension). Checks the extension AND that the content matches it."""
    extension = PurePath(filename).suffix.lower()
    kind = ALLOWED_EXTENSIONS.get(extension)
    if kind is None:
        raise UnsupportedFileType("Unsupported file type. Upload a PDF, .txt or .md file.")
    if kind == "pdf" and not data.startswith(b"%PDF-"):
        raise ExtractionError("This file is not a valid PDF.")
    return kind, extension


def extract_document(kind: str, data: bytes, max_pages: int, max_chars: int) -> ExtractedDocument:
    if kind == "pdf":
        return _extract_pdf(data, max_pages, max_chars)
    return _extract_text(data, max_chars)


def _extract_pdf(data: bytes, max_pages: int, max_chars: int) -> ExtractedDocument:
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError("This PDF is password-protected.")
        page_count = len(reader.pages)
        if page_count > max_pages:
            raise ExtractionError(f"This PDF has {page_count} pages. The limit is {max_pages}.")

        pages: list[PageText] = []
        total_chars = 0
        for number, page in enumerate(reader.pages, start=1):
            text = normalize_text(page.extract_text() or "")
            total_chars += len(text)
            if total_chars > max_chars:
                raise ExtractionError("This document contains too much text.")
            if text:
                pages.append(PageText(number, text))
    except ExtractionError:
        raise
    except Exception as error:  # the PDF parser can fail in many ways on damaged or hostile files
        logger.warning("PDF could not be parsed: %s", type(error).__name__)
        raise ExtractionError("Could not read this PDF. It may be damaged.") from error

    if not pages:
        raise ExtractionError("No text could be extracted. This may be a scanned PDF (pictures of text).")
    return ExtractedDocument(page_count, pages)


def _extract_text(data: bytes, max_chars: int) -> ExtractedDocument:
    if b"\x00" in data:
        raise ExtractionError("This does not look like a text file.")
    try:
        text = data.decode("utf-8-sig")  # also removes a leading byte-order mark
    except UnicodeDecodeError:
        raise ExtractionError("Text files must be UTF-8 encoded.") from None
    text = normalize_text(text)
    if not text:
        raise ExtractionError("The file contains no text.")
    if len(text) > max_chars:
        raise ExtractionError("This document contains too much text.")
    return ExtractedDocument(1, [PageText(1, text)])