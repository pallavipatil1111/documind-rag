import { createSseParser } from "./sse";
import type { DocumentInfo, StreamEvent } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {}

async function check(res: Response): Promise<Response> {
  if (res.ok) return res;
  let message = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail) && body.detail[0]?.msg) message = body.detail[0].msg;
  } catch {
    /* not JSON */
  }
  throw new ApiError(message);
}

async function call(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await check(await fetch(`${API_URL}${path}`, init));
  } catch (e) {
    if (e instanceof ApiError || (e as Error).name === "AbortError") throw e;
    throw new ApiError("Can't reach the server. It may be starting up; try again in a few seconds.");
  }
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  return (await call("/api/documents")).json();
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const form = new FormData();
  form.append("file", file);
  return (await call("/api/documents", { method: "POST", body: form })).json();
}

export async function deleteDocument(id: string): Promise<void> {
  await call(`/api/documents/${encodeURIComponent(id)}`, { method: "DELETE" });
}

/** Streams an answer; calls onEvent for each server-sent event until the stream ends. */
export async function askStream(
  body: { question: string; document_ids: string[]; history: { role: string; content: string }[] },
  onEvent: (e: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const res = await call("/api/ask/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.body) throw new ApiError("The server sent an empty response.");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const push = createSseParser();
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    push(decoder.decode(value, { stream: true })).forEach(onEvent);
  }
}
