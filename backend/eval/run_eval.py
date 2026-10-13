"""Compares chunking settings on retrieval quality and speed, and checks answers to unanswerable questions.

Usage (from backend/, with your .env loaded):
    python -m eval.run_eval                       # Pinecone + OpenAI embeddings, as configured
    python -m eval.run_eval --answers             # also asks the LLM the unanswerable questions
    VECTOR_STORE=memory EMBEDDING_PROVIDER=hashing python -m eval.run_eval   # offline smoke test

Each chunking setting is indexed in its own Pinecone namespace, and the namespaces are deleted
afterwards. Results are printed and written to eval/results.md.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import time
from pathlib import Path

from app import pdf
from app.chunking import chunk_pages, doc_id_for, langchain_splitter
from app.config import Settings
from app.embeddings import make_embeddings
from app.evaluation import relevance, summarise
from app.prompts import NOT_FOUND
from app.vectorstore import make_store

HERE = Path(__file__).parent
CONFIGS = [(400, 50), (800, 100), (1200, 200)]   # (chunk size, overlap) in characters
KS = [3, 5]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", action="store_true", help="also check answers to unanswerable questions")
    args = parser.parse_args()

    spec = json.loads((HERE / "questions.json").read_text())
    data = (HERE.parent / spec["document"]).read_bytes()
    base = Settings()
    pages = pdf.read_pages(data, base.max_pages)
    embeddings = make_embeddings(base)
    rows, best = [], None

    for size, overlap in CONFIGS:
        settings = dataclasses.replace(base, pinecone_namespace=f"eval-{size}-{overlap}")
        store = make_store(settings, embeddings)
        chunks = chunk_pages(pages, doc_id_for(data), Path(spec["document"]).name, langchain_splitter(size, overlap))
        store.add(chunks)
        time.sleep(2 if settings.vector_store == "pinecone" else 0)   # let the serverless index catch up

        flags, latencies = [], []
        for item in spec["questions"]:
            start = time.perf_counter()
            hits = store.search(item["q"], max(KS))
            latencies.append((time.perf_counter() - start) * 1000)
            flags.append(relevance([h.chunk.text for h in hits], item["evidence"]))
        for k in KS:
            report = summarise(flags, latencies, k)
            rows.append(report.row(f"{size} / {overlap} ({len(chunks)} chunks)"))
            if k == KS[-1] and (best is None or (report.mrr, -size) > (best[1].mrr, -best[0][0])):
                best = ((size, overlap), report)
        store.delete([c.id for c in chunks])

    table = "\n".join(["| Chunk size / overlap | k | Hit rate | MRR | Precision@k | p50 ms | p95 ms |",
                       "|---|---|---|---|---|---|---|", *rows])
    lines = [f"# Retrieval evaluation\n",
             f"{len(spec['questions'])} questions on `{spec['document']}`, embeddings: `{base.embedding_provider}` "
             f"({base.embedding_model if base.embedding_provider == 'openai' else 'offline hashing'}), store: `{base.vector_store}`.\n",
             table, ""]
    if best:
        lines.append(f"Best MRR at k={KS[-1]}: chunk size {best[0][0]}, overlap {best[0][1]} (MRR {best[1].mrr:.2f}).\n")

    if args.answers:
        from app.main import get_rag

        rag = get_rag()
        rag.ingest(Path(spec["document"]).name, data)
        refused = 0
        for q in spec["unanswerable"]:
            answer = rag.ask(q)["answer"]
            refused += NOT_FOUND.lower().rstrip(".") in answer.lower()
            lines.append(f"- *{q}* → {answer}")
        lines.insert(len(lines) - len(spec["unanswerable"]),
                     f"Unanswerable questions correctly refused: {refused}/{len(spec['unanswerable'])}\n")

    text = "\n".join(lines)
    print(text)
    (HERE / "results.md").write_text(text + "\n")


if __name__ == "__main__":
    main()
