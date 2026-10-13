export type DocumentInfo = {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  created_at: string;
  replaced?: boolean;
  ingest_ms?: number;
};

export type Source = {
  number: number;
  doc_id: string;
  filename: string;
  page: number;
  text: string;
  score: number;
};

export type AnswerStats = {
  cited: number[];
  retrieval_ms: number;
  first_token_ms: number | null;
  total_ms: number;
  model: string | null;
  context_tokens: number;
};

export type Message =
  | { role: "user"; id: string; content: string }
  | { role: "assistant"; id: string; content: string; sources: Source[]; stats?: AnswerStats; error?: string; pending: boolean };

export type StreamEvent =
  | { event: "sources"; data: Source[] }
  | { event: "token"; data: string }
  | { event: "done"; data: AnswerStats }
  | { event: "error"; data: string };
