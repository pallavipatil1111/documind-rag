"""Settings, read from environment variables (or a .env file loaded by the shell / docker compose)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


@dataclass(frozen=True)
class Settings:
    # Model providers
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    pinecone_api_key: str = field(default_factory=lambda: os.environ.get("PINECONE_API_KEY", ""))

    # "anthropic" or "openai" for answers; "openai" or "hashing" (offline, not semantic) for embeddings
    llm_provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "anthropic"))
    anthropic_model: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    openai_chat_model: str = field(default_factory=lambda: os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini"))
    embedding_provider: str = field(default_factory=lambda: os.environ.get("EMBEDDING_PROVIDER", "openai"))
    embedding_model: str = field(default_factory=lambda: os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"))
    embedding_dimension: int = field(default_factory=lambda: _int("EMBEDDING_DIMENSION", 1536))

    # "pinecone" or "memory" (in-process, for local development and tests)
    vector_store: str = field(default_factory=lambda: os.environ.get("VECTOR_STORE", "pinecone"))
    pinecone_index: str = field(default_factory=lambda: os.environ.get("PINECONE_INDEX", "documind"))
    pinecone_namespace: str = field(default_factory=lambda: os.environ.get("PINECONE_NAMESPACE", "default"))
    pinecone_cloud: str = field(default_factory=lambda: os.environ.get("PINECONE_CLOUD", "aws"))
    pinecone_region: str = field(default_factory=lambda: os.environ.get("PINECONE_REGION", "us-east-1"))

    # Chunking and retrieval
    chunk_size: int = field(default_factory=lambda: _int("CHUNK_SIZE", 1000))           # characters
    chunk_overlap: int = field(default_factory=lambda: _int("CHUNK_OVERLAP", 150))      # characters
    top_k: int = field(default_factory=lambda: _int("TOP_K", 5))
    min_score: float = field(default_factory=lambda: _float("MIN_SCORE", 0.25))         # cosine similarity
    context_token_budget: int = field(default_factory=lambda: _int("CONTEXT_TOKEN_BUDGET", 3000))
    max_answer_tokens: int = field(default_factory=lambda: _int("MAX_ANSWER_TOKENS", 800))

    # Uploads and storage
    max_upload_mb: int = field(default_factory=lambda: _int("MAX_UPLOAD_MB", 10))
    max_pages: int = field(default_factory=lambda: _int("MAX_PAGES", 300))
    database_path: str = field(default_factory=lambda: os.environ.get("DATABASE_PATH", "documind.db"))
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()))
