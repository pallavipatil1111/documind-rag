"use client";

import { useCallback, useEffect, useState } from "react";
import { listDocuments } from "@/lib/api";
import type { DocumentInfo } from "@/lib/types";
import Chat from "./Chat";
import DocumentPanel from "./DocumentPanel";

export default function Workspace() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
      setLoadError(null);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // forget selections for documents that were deleted
  useEffect(() => {
    setSelected((s) => s.filter((id) => documents.some((d) => d.id === id)));
  }, [documents]);

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex items-center justify-between border-b border-zinc-200 bg-white/80 px-4 py-3 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="flex items-center gap-2.5">
          <span aria-hidden className="grid size-8 place-items-center rounded-lg bg-[var(--color-accent)] text-sm font-bold text-white dark:text-zinc-950">D</span>
          <div>
            <h1 className="text-[15px] font-semibold leading-tight">DocuMind</h1>
            <p className="hidden text-xs text-zinc-500 sm:block dark:text-zinc-400">Answers from your documents, with sources</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setPanelOpen((o) => !o)}
          aria-expanded={panelOpen}
          aria-controls="documents-panel"
          className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm font-medium md:hidden dark:border-zinc-700"
        >
          Documents ({documents.length})
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside
          id="documents-panel"
          className={`${panelOpen ? "flex" : "hidden"} absolute inset-x-0 top-[57px] bottom-0 z-20 w-full flex-col border-r border-zinc-200 bg-white md:static md:flex md:w-80 md:shrink-0 dark:border-zinc-800 dark:bg-zinc-900`}
        >
          <DocumentPanel
            documents={documents}
            selected={selected}
            onSelectedChange={setSelected}
            onChanged={refresh}
            loadError={loadError}
            onClose={() => setPanelOpen(false)}
          />
        </aside>
        <main className="flex min-w-0 flex-1 flex-col">
          <Chat documents={documents} selected={selected} onOpenDocuments={() => setPanelOpen(true)} />
        </main>
      </div>
    </div>
  );
}
