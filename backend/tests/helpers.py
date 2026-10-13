"""Test doubles, so the pipeline can be tested without API keys or network."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.config import Settings
from app.context import approx_tokens
from app.embeddings import HashingEmbeddings
from app.llm import ExtractiveLLM
from app.rag import RagService
from app.registry import Registry
from app.vectorstore import MemoryStore

SAMPLE = Path(__file__).resolve().parent.parent / "sample_docs" / "aurora_handbook.pdf"


class SimpleSplitter:
    """Packs sentences into chunks of at most `size` characters, repeating the last sentence as overlap.
    Stands in for LangChain's splitter in tests that don't depend on its exact behaviour."""

    def __init__(self, size: int = 500, overlap: int = 80):
        self.size = size
        self.overlap = overlap

    def split_text(self, text: str) -> list[str]:
        import re

        sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n\n", text) if s.strip()]
        chunks, current = [], ""
        for s in sentences:
            if current and len(current) + len(s) + 1 > self.size:
                chunks.append(current.strip())
                tail = current[-self.overlap:] if self.overlap else ""
                current = tail[tail.find(" ") + 1:] if " " in tail else ""
            current += " " + s
        if current.strip():
            chunks.append(current.strip())
        return chunks


class SpyLLM(ExtractiveLLM):
    """Records calls, so tests can check when the model is (not) used."""

    def __init__(self):
        self.calls = 0

    def stream(self, system, messages, max_tokens):
        self.calls += 1
        self.last_messages = messages
        yield from super().stream(system, messages, max_tokens)


def make_service(**overrides) -> tuple[RagService, SpyLLM, MemoryStore]:
    defaults = dict(vector_store="memory", embedding_provider="hashing", llm_provider="extractive",
                    min_score=0.2, top_k=5, context_token_budget=1500,
                    database_path=os.path.join(tempfile.mkdtemp(), "test.db"))
    defaults.update(overrides)
    settings = Settings(**defaults)
    store = MemoryStore(HashingEmbeddings())
    llm = SpyLLM()
    return RagService(settings, store, llm, Registry(settings.database_path), SimpleSplitter(), approx_tokens), llm, store
