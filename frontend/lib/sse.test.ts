import assert from "node:assert/strict";
import { test } from "node:test";
import { createSseParser, splitCitations } from "./sse.ts";

test("parses events split across network chunks", () => {
  const push = createSseParser();
  assert.deepEqual(push('event: sources\ndata: [{"number":1}]\n\nevent: tok'), [{ event: "sources", data: [{ number: 1 }] }]);
  assert.deepEqual(push('en\ndata: "Hel'), []);
  assert.deepEqual(push('lo"\n\n'), [{ event: "token", data: "Hello" }]);
});

test("handles CRLF line endings and skips malformed events", () => {
  const push = createSseParser();
  assert.deepEqual(push("event: token\r\ndata: not json\r\n\r\nevent: done\r\ndata: {\"cited\":[1]}\r\n\r\n"), [
    { event: "done", data: { cited: [1] } },
  ]);
});

test("splits citations and ignores numbers with no source", () => {
  assert.deepEqual(splitCitations("Leave is 24 days [1]. See [3] and [2].", 2), ["Leave is 24 days ", 1, ". See [3] and ", 2, "."]);
  assert.deepEqual(splitCitations("No citations", 3), ["No citations"]);
});
