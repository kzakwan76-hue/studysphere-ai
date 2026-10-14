"""Page text normalisation and chunking.

Chunks are what we search and cite later, so each one keeps the page it came from. A chunk never
spans two pages, which keeps page references exact.
"""

import re
from dataclasses import dataclass

DEFAULT_MAX_CHARS = 800
DEFAULT_OVERLAP_CHARS = 100
# Where to cut, best first: paragraph break, sentence end, line break, any space.
_SEPARATORS = ("\n\n", ". ", "? ", "! ", "\n", " ")


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    position: int  # 0-based index across the whole document
    text: str


def normalize_text(text: str) -> str:
    """Unify newlines, drop NUL bytes, collapse spaces, keep paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _snap_end(text: str, start: int, end: int, min_length: int) -> int:
    """Pull the end of a chunk back to the best natural boundary, without making it tiny."""
    window = text[start:end]
    for separator in _SEPARATORS:
        index = window.rfind(separator)
        if index >= min_length:
            return start + index + len(separator)
    return end


def chunk_text(text: str, max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP_CHARS) -> list[str]:
    """Split text into chunks of at most max_chars, overlapping so ideas cut at a boundary survive."""
    if overlap < 0 or overlap >= max_chars // 2:
        raise ValueError("overlap must be smaller than half of max_chars")

    text = normalize_text(text)
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            end = _snap_end(text, start, end, min_length=max_chars // 2)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break

        next_start = end - overlap
        if next_start <= start:
            next_start = end  # too short to overlap: just keep moving
        else:
            while next_start < end and not text[next_start - 1].isspace():
                next_start += 1  # start the next chunk at the beginning of a word
        start = next_start
    return chunks


def chunk_pages(
    pages: list[PageText], max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP_CHARS
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page in pages:
        for piece in chunk_text(page.text, max_chars, overlap):
            chunks.append(TextChunk(page.page_number, len(chunks), piece))
    return chunks