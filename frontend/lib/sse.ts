import type { StreamEvent } from "./types";

/**
 * Incremental parser for server-sent events. Network chunks can split an event anywhere, so text is
 * buffered until a blank line ends an event. Returns the complete events and keeps the rest.
 */
export function createSseParser() {
  let buffer = "";
  return function push(chunk: string): StreamEvent[] {
    buffer += chunk.replace(/\r\n/g, "\n");
    const events: StreamEvent[] = [];
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let name = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) name = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
      }
      if (!data.length) continue;
      try {
        events.push({ event: name, data: JSON.parse(data.join("\n")) } as StreamEvent);
      } catch {
        // ignore malformed events rather than breaking the whole answer
      }
    }
    return events;
  };
}

/** Splits answer text into plain text and citation markers like [2], for rendering citation chips. */
export function splitCitations(text: string, sourceCount: number): Array<string | number> {
  const parts: Array<string | number> = [];
  const re = /\[(\d{1,2})\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const n = Number(m[1]);
    if (n < 1 || n > sourceCount) continue;
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(n);
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}
