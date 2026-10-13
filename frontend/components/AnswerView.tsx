"use client";

import { useState } from "react";
import { splitCitations } from "@/lib/sse";
import type { Message } from "@/lib/types";

type Assistant = Extract<Message, { role: "assistant" }>;

export default function AnswerView({ message }: { message: Assistant }) {
  const [active, setActive] = useState<number | null>(null);
  const cited = new Set(message.stats?.cited ?? []);
  const parts = splitCitations(message.content, message.sources.length);

  return (
    <article className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900" data-testid="answer">
      {message.pending && !message.content ? (
        <p className="flex items-center gap-2 text-sm text-zinc-500">
          <span aria-hidden className="size-3 animate-spin rounded-full border-2 border-zinc-300 border-t-[var(--color-accent)]" />
          {message.sources.length ? `Found ${message.sources.length} relevant passages. Writing the answer…` : "Searching your documents…"}
        </p>
      ) : (
        <p className="whitespace-pre-wrap text-[15px] leading-relaxed" data-testid="answer-text">
          {parts.map((p, i) =>
            typeof p === "number" ? (
              <button
                key={i}
                type="button"
                onClick={() => setActive(active === p ? null : p)}
                aria-label={`Source ${p}`}
                className="mx-0.5 inline-grid h-5 min-w-5 place-items-center rounded-md bg-[var(--color-accent-soft)] px-1 align-[1px] font-mono text-[11px] font-semibold text-[var(--color-accent)]"
              >
                {p}
              </button>
            ) : (
              <span key={i}>{p}</span>
            ),
          )}
          {message.pending && <span aria-hidden className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-zinc-400 align-middle" />}
        </p>
      )}

      {message.error && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{message.error}</p>}

      {message.sources.length > 0 && !message.pending && (
        <details className="mt-4 group" open={active !== null}>
          <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Sources ({message.sources.length})
          </summary>
          <ol className="mt-2 space-y-2" data-testid="sources">
            {message.sources.map((s) => (
              <li
                key={s.number}
                className={`rounded-xl border p-3 text-sm transition-colors ${
                  active === s.number ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]" : "border-zinc-200 dark:border-zinc-800"
                }`}
              >
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500">
                  <span className="font-mono font-semibold text-[var(--color-accent)]">[{s.number}]</span>
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">{s.filename}</span>
                  <span>page {s.page}</span>
                  <span>· match {Math.round(s.score * 100)}%</span>
                  {!cited.has(s.number) && <span className="rounded bg-zinc-100 px-1.5 dark:bg-zinc-800">not cited</span>}
                </div>
                <p className="mt-1.5 line-clamp-4 text-zinc-700 dark:text-zinc-300">{s.text}</p>
              </li>
            ))}
          </ol>
        </details>
      )}

      {message.stats && (
        <p className="mt-3 font-mono text-[11px] text-zinc-400" data-testid="answer-stats">
          retrieval {message.stats.retrieval_ms} ms
          {message.stats.first_token_ms !== null && ` · first word ${message.stats.first_token_ms} ms`} · total {message.stats.total_ms} ms
          {message.stats.context_tokens > 0 && ` · ${message.stats.context_tokens} context tokens`}
          {message.stats.model && ` · ${message.stats.model}`}
        </p>
      )}
    </article>
  );
}
