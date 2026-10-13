"""Splits pages into overlapping chunks with LangChain's RecursiveCharacterTextSplitter.

The splitter tries paragraph breaks first, then line breaks, then sentences, then words, so chunks
end at natural boundaries where possible. Overlap keeps a sentence that straddles two chunks
retrievable from either side. Chunking is per page so every chunk has exactly one page number to cite.
"""
from __future__ import annotations

import hashlib
from typing import Callable, Iterable, Protocol

from .models import Chunk, Page

SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]


class TextSplitter(Protocol):
    def split_text(self, text: str) -> list[str]: ...


def langchain_splitter(chunk_size: int, chunk_overlap: int) -> TextSplitter:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
        keep_separator="end",
        strip_whitespace=True,
    )


def chunk_id(doc_id: str, index: int) -> str:
    return f"{doc_id}-{index:05d}"


def doc_id_for(data: bytes) -> str:
    """Same file, same id: re-uploading a document replaces it instead of duplicating it."""
    return hashlib.sha256(data).hexdigest()[:16]


def chunk_pages(pages: Iterable[Page], doc_id: str, filename: str, splitter: TextSplitter,
                min_chars: int = 40) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for piece in splitter.split_text(page.text):
            piece = piece.strip()
            if len(piece) < min_chars:      # page numbers, stray headers
                continue
            chunks.append(Chunk(chunk_id(doc_id, len(chunks)), doc_id, filename, page.number, len(chunks), piece))
    return chunks


SplitterFactory = Callable[[int, int], TextSplitter]
