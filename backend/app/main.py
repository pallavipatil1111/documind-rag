"""FastAPI app: upload PDFs, list and delete them, ask questions (streamed with server-sent events)."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .chunking import langchain_splitter
from .config import Settings
from .context import token_counter
from .embeddings import make_embeddings
from .llm import make_llm
from .rag import RagService, UploadError
from .registry import Registry
from .vectorstore import make_store

log = logging.getLogger("documind")


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_rag() -> RagService:
    s = get_settings()
    embeddings = make_embeddings(s)
    return RagService(s, make_store(s, embeddings), make_llm(s), Registry(s.database_path),
                      langchain_splitter(s.chunk_size, s.chunk_overlap), token_counter())


Rag = Annotated[RagService, Depends(get_rag)]

app = FastAPI(title="DocuMind API", version="1.0.0",
              description="Upload PDFs and ask questions about them. Answers are grounded in retrieved passages and cite their sources.")
app.add_middleware(CORSMiddleware, allow_origins=list(get_settings().cors_origins), allow_methods=["GET", "POST", "DELETE"],
                   allow_headers=["Content-Type"])


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=8000)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    history: list[Turn] = Field(default_factory=list, max_length=10)


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "llm": s.llm_provider, "embeddings": s.embedding_provider, "vector_store": s.vector_store}


@app.get("/api/documents")
def list_documents(rag: Rag) -> list[dict]:
    return rag.documents()


@app.post("/api/documents", status_code=201)
async def upload(rag: Rag, file: UploadFile = File(...)) -> dict:
    data = await file.read()
    try:
        return rag.ingest(file.filename or "document.pdf", data)
    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, rag: Rag) -> None:
    if not rag.delete(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")


@app.post("/api/ask")
def ask(req: AskRequest, rag: Rag) -> dict:
    """Whole answer at once."""
    return rag.ask(req.question, req.document_ids, [t.model_dump() for t in req.history])


@app.post("/api/ask/stream")
def ask_stream(req: AskRequest, rag: Rag) -> StreamingResponse:
    """Server-sent events: `sources`, then `token` events as the answer is written, then `done`."""
    def events():
        try:
            for kind, value in rag.ask_stream(req.question, req.document_ids, [t.model_dump() for t in req.history]):
                yield f"event: {kind}\ndata: {json.dumps(value)}\n\n"
        except Exception:  # noqa: BLE001 - report to the client instead of cutting the stream
            log.exception("answer failed")
            yield f"event: error\ndata: {json.dumps('The model could not answer right now. Please try again.')}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
