"""HTTP tests. They need FastAPI (pip install -r requirements-dev.txt) and are skipped without it."""
import importlib.util
import json
import unittest

from tests.helpers import SAMPLE, make_service

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(HAS_FASTAPI, "fastapi and httpx are not installed")
class ApiTest(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient

        from app.main import app, get_rag

        self.rag, _, _ = make_service()
        app.dependency_overrides[get_rag] = lambda: self.rag
        self.client = TestClient(app)
        self.addCleanup(app.dependency_overrides.clear)

    def upload(self):
        return self.client.post("/api/documents", files={"file": ("handbook.pdf", SAMPLE.read_bytes(), "application/pdf")})

    def test_upload_list_ask_delete(self):
        r = self.upload()
        self.assertEqual(r.status_code, 201)
        doc = r.json()
        self.assertEqual(doc["pages"], 6)
        self.assertEqual(self.client.get("/api/documents").json()[0]["id"], doc["id"])

        answer = self.client.post("/api/ask", json={"question": "What is the probation period for new joiners?"}).json()
        self.assertIn("[1]", answer["answer"])
        self.assertEqual(answer["sources"][0]["page"], 5)

        self.assertEqual(self.client.delete(f"/api/documents/{doc['id']}").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/documents/{doc['id']}").status_code, 404)

    def test_streaming_answer_uses_server_sent_events(self):
        self.upload()
        with self.client.stream("POST", "/api/ask/stream", json={"question": "What is Build Friday?"}) as r:
            self.assertTrue(r.headers["content-type"].startswith("text/event-stream"))
            body = "".join(r.iter_text())
        events = [block.split("\n")[0].removeprefix("event: ") for block in body.strip().split("\n\n")]
        self.assertEqual(events[0], "sources")
        self.assertEqual(events[-1], "done")
        sources = json.loads(body.split("\n\n")[0].split("data: ", 1)[1])
        self.assertEqual(sources[0]["page"], 5)

    def test_bad_uploads_and_questions_are_rejected(self):
        r = self.client.post("/api/documents", files={"file": ("x.pdf", b"nope", "application/pdf")})
        self.assertEqual(r.status_code, 400)
        self.assertIn("isn't a PDF", r.json()["detail"])
        self.assertEqual(self.client.post("/api/ask", json={"question": ""}).status_code, 422)
