"use client";

import { useRef, useState } from "react";
import { deleteDocument, uploadDocument } from "@/lib/api";
import type { DocumentInfo } from "@/lib/types";

type Props = {
  documents: DocumentInfo[];
  selected: string[];
  onSelectedChange: (ids: string[]) => void;
  onChanged: () => Promise<void>;
  loadError: string | null;
  onClose: () => void;
};

const MAX_MB = 10;

export default function DocumentPanel({ documents, selected, onSelectedChange, onChanged, loadError, onClose }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [status, setStatus] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [dragging, setDragging] = useState(false);

  async function upload(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setStatus({ kind: "error", text: `${file.name} isn't a PDF.` });
        continue;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        setStatus({ kind: "error", text: `${file.name} is larger than ${MAX_MB} MB.` });
        continue;
      }
      setBusy(`Reading and indexing ${file.name}…`);
      setStatus(null);
      try {
        const doc = await uploadDocument(file);
        setStatus({
          kind: "ok",
          text: `${doc.replaced ? "Updated" : "Added"} ${doc.filename}: ${doc.pages} pages, ${doc.chunks} chunks.`,
        });
        await onChanged();
      } catch (e) {
        setStatus({ kind: "error", text: (e as Error).message });
      } finally {
        setBusy(null);
      }
    }
  }

  async function remove(doc: DocumentInfo) {
    if (!confirm(`Remove ${doc.filename}? Its passages are deleted from the index.`)) return;
    try {
      await deleteDocument(doc.id);
      setStatus({ kind: "ok", text: `Removed ${doc.filename}.` });
      await onChanged();
    } catch (e) {
      setStatus({ kind: "error", text: (e as Error).message });
    }
  }

  function toggle(id: string) {
    onSelectedChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Documents</h2>
        <button type="button" onClick={onClose} className="text-sm text-zinc-500 md:hidden">
          Done
        </button>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(e.dataTransfer.files);
        }}
        className={`rounded-xl border border-dashed p-4 text-center transition-colors ${
          dragging ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]" : "border-zinc-300 dark:border-zinc-700"
        }`}
      >
        <p className="text-sm text-zinc-600 dark:text-zinc-300">Drop PDFs here, or</p>
        <button
          type="button"
          disabled={!!busy}
          onClick={() => input.current?.click()}
          className="mt-2 rounded-lg bg-[var(--color-accent)] px-3.5 py-2 text-sm font-semibold text-white disabled:opacity-60 dark:text-zinc-950"
        >
          Choose files
        </button>
        <p className="mt-2 text-xs text-zinc-500">PDF with selectable text, up to {MAX_MB} MB</p>
        <input
          ref={input}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          data-testid="file-input"
          onChange={(e) => {
            if (e.target.files) upload(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <div role="status" aria-live="polite" className="min-h-0 text-sm">
        {busy && (
          <p className="flex items-center gap-2 text-zinc-600 dark:text-zinc-300">
            <span aria-hidden className="size-3 animate-spin rounded-full border-2 border-zinc-300 border-t-[var(--color-accent)]" />
            {busy}
          </p>
        )}
        {status && (
          <p className={status.kind === "error" ? "text-red-600 dark:text-red-400" : "text-emerald-700 dark:text-emerald-400"} data-testid="upload-status">
            {status.text}
          </p>
        )}
        {loadError && <p className="text-red-600 dark:text-red-400">{loadError}</p>}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {documents.length === 0 ? (
          <p className="text-sm text-zinc-500">No documents yet. Upload a PDF to start asking questions.</p>
        ) : (
          <>
            <p className="mb-2 text-xs text-zinc-500">
              {selected.length ? `Searching ${selected.length} of ${documents.length}` : "Searching all documents"}. Tick to narrow it down.
            </p>
            <ul className="space-y-1.5" data-testid="document-list">
              {documents.map((d) => (
                <li key={d.id} className="group flex items-start gap-2.5 rounded-lg p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800">
                  <input
                    type="checkbox"
                    id={`doc-${d.id}`}
                    checked={selected.includes(d.id)}
                    onChange={() => toggle(d.id)}
                    className="mt-1 size-4 accent-[var(--color-accent)]"
                  />
                  <label htmlFor={`doc-${d.id}`} className="min-w-0 flex-1 cursor-pointer">
                    <span className="block truncate text-sm font-medium" title={d.filename}>
                      {d.filename}
                    </span>
                    <span className="text-xs text-zinc-500">
                      {d.pages} pages · {d.chunks} chunks
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={() => remove(d)}
                    aria-label={`Remove ${d.filename}`}
                    className="rounded px-1.5 text-zinc-400 hover:text-red-600 md:opacity-0 md:group-hover:opacity-100 md:focus:opacity-100"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
