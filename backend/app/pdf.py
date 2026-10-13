"""PDF text extraction, page by page, so every chunk keeps its page number for citations."""
from __future__ import annotations

import io
import re

from .models import Page


class PdfError(ValueError):
    """The upload isn't a readable PDF, or has no extractable text."""


_SPACES = re.compile(r"[ \t ]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def clean(text: str) -> str:
    """Normalises whitespace and re-joins words hyphenated across line breaks."""
    text = text.replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANK_LINES.sub("\n\n", text).strip()


def read_pages(data: bytes, max_pages: int) -> list[Page]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    if not data.startswith(b"%PDF"):
        raise PdfError("That file isn't a PDF.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise PdfError("The PDF is password-protected.")
        if len(reader.pages) > max_pages:
            raise PdfError(f"The PDF has {len(reader.pages)} pages; the limit is {max_pages}.")
        pages = [Page(i + 1, clean(p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    except PdfReadError as e:
        raise PdfError("The PDF couldn't be read. It may be damaged.") from e
    pages = [p for p in pages if p.text]
    if not pages:
        raise PdfError("No text was found in the PDF. Scanned PDFs need OCR first.")
    return pages
