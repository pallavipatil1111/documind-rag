"""The RAG pipeline: ingest documents, retrieve passages, generate cited answers."""
from __future__ import annotations

import time
from dataclasses import asdict
from typing import Callable, Iterator, Sequence

from . import pdf
from .chunking import TextSplitter, chunk_pages, doc_id_for
from .config import Settings
from .context import select_sources
from .llm import LLM
from .models import DocumentInfo, Source
from .prompts import NOT_FOUND, SYSTEM_PROMPT, build_messages, cited_numbers
from .registry import Registry
from .vectorstore import VectorStore


class UploadError(ValueError):
    """The upload was refused (too big, not a PDF, no text)."""


def _ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


class RagService:
    def __init__(self, settings: Settings, store: VectorStore, llm: LLM, registry: Registry,
                 splitter: TextSplitter, count_tokens: Callable[[str], int]):
        self.settings = settings
        self.store = store
        self.llm = llm
        self.registry = registry
        self.splitter = splitter
        self.count_tokens = count_tokens

    # ------------------------------------------------------------------ documents

    def ingest(self, filename: str, data: bytes) -> dict:
        """PDF → pages → chunks → embeddings in the vector store. Re-uploading the same file replaces it."""
        start = time.perf_counter()
        if len(data) > self.settings.max_upload_mb * 1024 * 1024:
            raise UploadError(f"The file is larger than {self.settings.max_upload_mb} MB.")
        if not filename.lower().endswith(".pdf"):
            raise UploadError("Only PDF files are supported.")
        try:
            pages = pdf.read_pages(data, self.settings.max_pages)
        except pdf.PdfError as e:
            raise UploadError(str(e)) from e

        doc_id = doc_id_for(data)
        existing = self.registry.get(doc_id)
        if existing:
            self.store.delete(existing.chunk_ids)
        chunks = chunk_pages(pages, doc_id, filename, self.splitter)
        if not chunks:
            raise UploadError("The PDF didn't contain enough text to index.")
        self.store.add(chunks)
        doc = DocumentInfo(doc_id, filename, len(pages), len(chunks), Registry.now(), [c.id for c in chunks])
        self.registry.save(doc)
        return {**self.describe(doc), "replaced": existing is not None, "ingest_ms": _ms(start)}

    def documents(self) -> list[dict]:
        return [self.describe(d) for d in self.registry.all()]

    def delete(self, doc_id: str) -> bool:
        doc = self.registry.get(doc_id)
        if not doc:
            return False
        self.store.delete(doc.chunk_ids)
        self.registry.delete(doc_id)
        return True

    @staticmethod
    def describe(doc: DocumentInfo) -> dict:
        return {"id": doc.id, "filename": doc.filename, "pages": doc.pages, "chunks": doc.chunks,
                "created_at": doc.created_at}

    # ------------------------------------------------------------------ questions

    def retrieve(self, question: str, doc_ids: Sequence[str] | None = None, k: int | None = None) -> list[Source]:
        hits = self.store.search(question, k or self.settings.top_k, doc_ids or None)
        return select_sources(hits, self.settings.min_score, self.settings.context_token_budget, self.count_tokens)

    def ask_stream(self, question: str, doc_ids: Sequence[str] | None = None,
                   history: Sequence[dict] = ()) -> Iterator[tuple[str, object]]:
        """Yields ("sources", [...]) first, then ("token", text) pieces, then ("done", stats).

        If nothing relevant is retrieved the model isn't called at all: the answer is "not found"
        straight away, which saves cost and avoids the model guessing.
        """
        start = time.perf_counter()
        sources = self.retrieve(question, doc_ids)
        retrieval_ms = _ms(start)
        yield "sources", [asdict(s) for s in sources]

        if not sources:
            yield "token", NOT_FOUND
            yield "done", {"cited": [], "retrieval_ms": retrieval_ms, "first_token_ms": None,
                           "total_ms": _ms(start), "model": None, "context_tokens": 0}
            return

        messages = build_messages(question, sources, history)
        answer: list[str] = []
        first_token_ms = None
        for piece in self.llm.stream(SYSTEM_PROMPT, messages, self.settings.max_answer_tokens):
            if first_token_ms is None:
                first_token_ms = _ms(start)
            answer.append(piece)
            yield "token", piece
        text = "".join(answer)
        yield "done", {"cited": cited_numbers(text, len(sources)), "retrieval_ms": retrieval_ms,
                       "first_token_ms": first_token_ms, "total_ms": _ms(start), "model": self.llm.name,
                       "context_tokens": sum(self.count_tokens(s.text) for s in sources)}

    def ask(self, question: str, doc_ids: Sequence[str] | None = None, history: Sequence[dict] = ()) -> dict:
        """Non-streaming version of ask_stream, for API clients and the evaluation script."""
        result: dict = {"answer": ""}
        for kind, value in self.ask_stream(question, doc_ids, history):
            if kind == "sources":
                result["sources"] = value
            elif kind == "token":
                result["answer"] += value
            else:
                result.update(value)
        result["answer"] = result["answer"].strip()
        return result
