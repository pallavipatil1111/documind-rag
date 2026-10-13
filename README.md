# DocuMind: RAG document Q&A assistant

Upload PDFs, ask questions in plain English, and get answers **grounded in your documents with
page-level citations**. DocuMind is a full Retrieval-Augmented Generation (RAG) application:
LangChain ingestion and chunking, OpenAI embeddings in a Pinecone vector database, answers written
by Claude (or OpenAI), a Next.js + Tailwind CSS interface, and a retrieval evaluation to tune it all.

<p>
  <img src="docs/screenshot.png" alt="DocuMind answering a question with citations" width="68%">
  <img src="docs/screenshot-mobile.png" alt="DocuMind on a phone" width="24%">
</p>

*Screenshots taken in offline mode (no API keys), where the answer is a quote from the best passage.*

## How it works

```
 PDF ──► pypdf (text per page) ──► LangChain RecursiveCharacterTextSplitter ──► chunks with page numbers
                                                                                 │
                                         OpenAI text-embedding-3-small (1536-d) ◄┘
                                                                                 │
                                    Pinecone serverless index (cosine) ◄─────────┘  + doc, file, page metadata

 Question ──► embed ──► Pinecone top-k (optionally filtered to chosen documents)
          ──► context selection: drop weak matches, drop near-duplicates, fit a token budget
          ──► prompt: numbered sources + rules ("answer only from sources, cite [n], else say not found")
          ──► Claude / OpenAI, streamed to the browser over server-sent events
          ──► answer with clickable [n] citations → source cards (file, page, match score)
```

### Design decisions

| Decision | Why |
|---|---|
| **Chunk per page**, recursive splitting (paragraph → line → sentence → word), 1,000 characters with 150 overlap | Every chunk has exactly one page to cite; boundaries fall at natural breaks; overlap keeps sentences that straddle a boundary findable. The size and overlap were chosen with the evaluation below |
| **Similarity threshold** (`MIN_SCORE`) before generation | Weak matches add noise and cost. If nothing passes, the model isn't called and the answer is "I couldn't find that in your documents", so it can't make something up |
| **Near-duplicate removal** (word overlap ≥ 80%) | Overlapping chunks repeat text; duplicates waste the context window |
| **Token budget** for context (`CONTEXT_TOKEN_BUDGET`, counted with tiktoken) | Keeps prompts a predictable size and cost however many documents there are |
| **Numbered sources + citation rule** in the prompt, temperature 0 | Every claim can be checked against the page it came from; answers are repeatable |
| **Prompt-injection guard** | The prompt tells the model that document text is content, not instructions |
| **Same file → same id** (SHA-256 of the bytes) | Re-uploading a document replaces its vectors instead of duplicating them |
| **Delete by vector id** | Pinecone serverless indexes don't delete by metadata, so each document's vector ids are stored |
| **Streaming** (server-sent events) | The first words appear in about the time retrieval takes, instead of after the whole answer |
| **Pluggable providers** | Claude or OpenAI for answers; Pinecone or in-memory store; offline mode for tests without keys |

## Retrieval evaluation

[`backend/eval/`](backend/eval) holds 22 questions about the sample handbook, each with the passage that
answers it, plus 3 questions the handbook can't answer. `run_eval.py` indexes the document with several
chunk sizes and measures:

- **Hit rate @k**: how often the right passage is in the top *k* results
- **MRR** (mean reciprocal rank): 1.0 if it's always first, 0.5 if it's always second
- **Precision @k**: how much of what's retrieved is relevant
- **Latency**: p50 and p95 search time
- **Refusals**: with `--answers`, whether the model correctly says it can't answer the 3 unanswerable questions

```bash
cd backend
python -m eval.run_eval --answers     # uses your .env (OpenAI + Pinecone + Claude); writes eval/results.md
```

## Run it locally

**Backend** (Python 3.11+):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                     # add your API keys
uvicorn app.main:app --reload                            # http://localhost:8000/docs
```

**Frontend** (Node 20+):

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev                                              # http://localhost:3000
```

Try it with [`backend/sample_docs/aurora_handbook.pdf`](backend/sample_docs) (an invented company handbook),
for example: *"How much is the yearly learning budget?"* or *"Can I copy patient data to my laptop?"*

No keys yet? In `backend/.env` set `LLM_PROVIDER=extractive`, `EMBEDDING_PROVIDER=hashing` and
`VECTOR_STORE=memory`. Everything works offline, but search only matches words and the "answer" is a quote.

Or run both with Docker: `docker compose up --build`.

### API keys

| Key | Where | Used for |
|---|---|---|
| `ANTHROPIC_API_KEY` | platform.claude.com → Settings → API Keys | Writing answers |
| `OPENAI_API_KEY` | platform.openai.com → API keys | Embeddings (and answers if `LLM_PROVIDER=openai`) |
| `PINECONE_API_KEY` | app.pinecone.io → API Keys (free Starter plan) | Vector database; the index is created on first start |

Keys go only in `backend/.env` (ignored by git) or your hosting provider's settings.

## Deploy

- **Backend → Render**: New → Blueprint → this repo ([`render.yaml`](render.yaml)). Add the three keys, and set
  `CORS_ORIGINS` to your Vercel URL. The free plan sleeps when idle, so the first request takes a little longer.
- **Frontend → Vercel**: import the repo, set the root directory to `frontend` and add
  `NEXT_PUBLIC_API_URL` = your Render URL.

The document list is kept in SQLite. On Render's free plan the disk resets on redeploy (the vectors stay in
Pinecone), so attach a disk at `/data` or re-upload after a deploy.

## API

Interactive docs at `/docs` (FastAPI / OpenAPI).

| Method | Path | What |
|---|---|---|
| POST | `/api/documents` | Upload a PDF (multipart `file`); returns pages, chunks and indexing time |
| GET | `/api/documents` | Uploaded documents |
| DELETE | `/api/documents/{id}` | Remove a document and its vectors |
| POST | `/api/ask` | `{question, document_ids?, history?}` → answer, sources, citations, timings |
| POST | `/api/ask/stream` | Same, as server-sent events: `sources`, `token`…, `done` |
| GET | `/health` | Status and configured providers |

## Tests

| Suite | What it covers |
|---|---|
| `backend/tests/test_pdf_and_chunking.py` | Page extraction, page limits, non-PDFs, scanned PDFs, hyphen repair, chunk ids and page numbers |
| `backend/tests/test_context_and_prompts.py` | Similarity threshold, de-duplication, token budget, prompt format, history trimming, citation parsing |
| `backend/tests/test_rag.py` | The whole pipeline with an in-memory store: right page retrieved, streamed events, refusal without calling the model, document filters, re-upload, delete, upload limits, follow-up questions |
| `backend/tests/test_api.py` | HTTP endpoints, server-sent events, validation |
| `backend/tests/test_evaluation.py` | Hit rate, MRR, precision@k, percentiles |
| `frontend/lib/sse.test.ts` | Streaming parser (events split across network chunks) and citation rendering |

```bash
cd backend && pytest -q
cd frontend && npm test && npm run typecheck
```

GitHub Actions runs all of these, an offline evaluation and a production build of the frontend on every push.

## Project structure

```
backend/
├── app/
│   ├── main.py          FastAPI routes, streaming
│   ├── rag.py           pipeline: ingest, retrieve, answer
│   ├── pdf.py           page-by-page text extraction
│   ├── chunking.py      LangChain recursive splitter, chunk ids
│   ├── embeddings.py    OpenAI embeddings (+ offline hashing)
│   ├── vectorstore.py   Pinecone via LangChain (+ in-memory)
│   ├── context.py       threshold, de-duplication, token budget
│   ├── prompts.py       system prompt, sources block, citations
│   ├── llm.py           Claude / OpenAI streaming clients
│   ├── registry.py      uploaded documents (SQLite)
│   └── evaluation.py    retrieval metrics
├── eval/                questions with evidence, evaluation runner
├── sample_docs/         sample handbook PDF and the script that makes it
└── tests/
frontend/
├── app/                 Next.js App Router (layout, page, Tailwind CSS)
├── components/          Workspace, DocumentPanel, Chat, AnswerView
└── lib/                 API client, SSE parser, types
```

---
Built by **Pallavi Patil** · [LinkedIn](https://www.linkedin.com/in/pallavi-patil-6baa13253) · [GitHub](https://github.com/pallavipatil1111)
