"use client";

import { useEffect, useRef, useState } from "react";
import { askStream } from "@/lib/api";
import type { DocumentInfo, Message } from "@/lib/types";
import AnswerView from "./AnswerView";

type Props = { documents: DocumentInfo[]; selected: string[]; onOpenDocuments: () => void };

const SUGGESTIONS = ["Summarise the key points", "What are the deadlines or dates mentioned?", "What does it say about costs?"];

let counter = 0;
const nextId = () => `m${++counter}`;

export default function Chat({ documents, selected, onOpenDocuments }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  function update(id: string, change: (m: Extract<Message, { role: "assistant" }>) => Partial<Message>) {
    setMessages((all) => all.map((m) => (m.id === id && m.role === "assistant" ? ({ ...m, ...change(m) } as Message) : m)));
  }

  async function ask(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    const history = messages
      .filter((m) => m.role === "user" || (!m.pending && !m.error))
      .slice(-4)
      .map((m) => ({ role: m.role, content: m.content }));
    const answerId = nextId();
    setMessages((m) => [...m, { role: "user", id: nextId(), content: q }, { role: "assistant", id: answerId, content: "", sources: [], pending: true }]);
    setQuestion("");
    setBusy(true);
    abort.current = new AbortController();
    try {
      await askStream(
        { question: q, document_ids: selected, history },
        (e) => {
          if (e.event === "sources") update(answerId, () => ({ sources: e.data }));
          else if (e.event === "token") update(answerId, (m) => ({ content: m.content + e.data }));
          else if (e.event === "done") update(answerId, () => ({ stats: e.data, pending: false }));
          else if (e.event === "error") update(answerId, () => ({ error: e.data, pending: false }));
        },
        abort.current.signal,
      );
      update(answerId, () => ({ pending: false }));
    } catch (e) {
      const stopped = (e as Error).name === "AbortError";
      update(answerId, (m) => ({ pending: false, error: stopped ? (m.content ? undefined : "Stopped.") : (e as Error).message }));
    } finally {
      setBusy(false);
      abort.current = null;
    }
  }

  const scope = selected.length ? `${selected.length} selected document${selected.length > 1 ? "s" : ""}` : "all documents";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto" data-testid="conversation">
        <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
          {messages.length === 0 && (
            <div className="mt-10 text-center sm:mt-20">
              <h2 className="text-2xl font-semibold tracking-tight">Ask your documents anything</h2>
              <p className="mx-auto mt-2 max-w-md text-sm text-zinc-500 dark:text-zinc-400">
                Answers come only from the PDFs you upload, and every claim links to the page it came from.
              </p>
              {documents.length === 0 ? (
                <button type="button" onClick={onOpenDocuments} className="mt-6 text-sm font-medium text-[var(--color-accent)] md:hidden">
                  Upload a PDF to begin →
                </button>
              ) : (
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => ask(s)}
                      className="rounded-full border border-zinc-200 bg-white px-3.5 py-1.5 text-sm hover:border-[var(--color-accent)] dark:border-zinc-700 dark:bg-zinc-900"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {messages.map((m) =>
            m.role === "user" ? (
              <div key={m.id} className="self-end rounded-2xl rounded-br-md bg-[var(--color-accent)] px-4 py-2.5 text-[15px] text-white dark:text-zinc-950" data-testid="user-message">
                {m.content}
              </div>
            ) : (
              <AnswerView key={m.id} message={m} />
            ),
          )}
          <div ref={bottom} />
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        className="border-t border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <label htmlFor="question" className="sr-only">
            Your question
          </label>
          <textarea
            id="question"
            rows={1}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                ask(question);
              }
            }}
            maxLength={1000}
            placeholder={documents.length ? `Ask about ${scope}…` : "Upload a PDF first"}
            disabled={!documents.length}
            className="max-h-40 min-h-11 flex-1 resize-none rounded-xl border border-zinc-200 bg-zinc-50 px-3.5 py-2.5 text-[15px] focus:border-[var(--color-accent)] focus:outline-none disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950"
          />
          {busy ? (
            <button type="button" onClick={() => abort.current?.abort()} className="h-11 rounded-xl border border-zinc-300 px-4 text-sm font-semibold dark:border-zinc-600">
              Stop
            </button>
          ) : (
            <button type="submit" disabled={!question.trim() || !documents.length} className="h-11 rounded-xl bg-[var(--color-accent)] px-4 text-sm font-semibold text-white disabled:opacity-50 dark:text-zinc-950">
              Ask
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
