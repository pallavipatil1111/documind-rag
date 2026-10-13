import unittest

from app.prompts import NOT_FOUND
from app.rag import UploadError
from tests.helpers import SAMPLE, make_service


class RagPipelineTest(unittest.TestCase):
    def setUp(self):
        self.rag, self.llm, self.store = make_service()
        self.doc = self.rag.ingest("aurora_handbook.pdf", SAMPLE.read_bytes())

    def test_ingest_indexes_every_chunk_and_records_the_document(self):
        self.assertEqual(self.doc["pages"], 6)
        self.assertGreater(self.doc["chunks"], 6)
        self.assertEqual(len(self.store.rows), self.doc["chunks"])
        self.assertEqual(self.rag.documents()[0]["filename"], "aurora_handbook.pdf")

    def test_retrieval_finds_the_right_page(self):
        sources = self.rag.retrieve("How many days of paid annual leave do employees get?")
        self.assertEqual(sources[0].page, 2)
        self.assertIn("24 days of paid annual leave", " ".join(sources[0].text.split()))

    def test_answer_streams_sources_then_tokens_then_stats(self):
        events = list(self.rag.ask_stream("What is the yearly learning budget?"))
        kinds = [k for k, _ in events]
        self.assertEqual(kinds[0], "sources")
        self.assertEqual(kinds[-1], "done")
        self.assertIn("token", kinds)
        answer = "".join(v for k, v in events if k == "token")
        self.assertIn("[1]", answer)
        done = events[-1][1]
        self.assertEqual(done["cited"], [1])
        self.assertGreater(done["context_tokens"], 0)

    def test_unrelated_question_is_refused_without_calling_the_model(self):
        result = self.rag.ask("quantum chromodynamics gluon lattice")
        self.assertEqual(result["answer"], NOT_FOUND)
        self.assertEqual(result["sources"], [])
        self.assertEqual(self.llm.calls, 0)

    def test_search_can_be_limited_to_chosen_documents(self):
        self.assertEqual(self.rag.retrieve("annual leave", doc_ids=["someone-else"]), [])

    def test_reupload_replaces_instead_of_duplicating(self):
        again = self.rag.ingest("renamed.pdf", SAMPLE.read_bytes())
        self.assertTrue(again["replaced"])
        self.assertEqual(len(self.rag.documents()), 1)
        self.assertEqual(len(self.store.rows), again["chunks"])

    def test_delete_removes_the_vectors_too(self):
        self.assertTrue(self.rag.delete(self.doc["id"]))
        self.assertEqual(self.store.rows, {})
        self.assertEqual(self.rag.documents(), [])
        self.assertFalse(self.rag.delete(self.doc["id"]))

    def test_upload_limits(self):
        with self.assertRaisesRegex(UploadError, "Only PDF"):
            self.rag.ingest("notes.txt", b"%PDF-fake")
        with self.assertRaisesRegex(UploadError, "isn't a PDF"):
            self.rag.ingest("notes.pdf", b"plain text")
        small, _, _ = make_service(max_upload_mb=0)
        with self.assertRaisesRegex(UploadError, "larger than"):
            small.ingest("a.pdf", SAMPLE.read_bytes())

    def test_follow_up_questions_carry_recent_history(self):
        history = [{"role": "user", "content": "Tell me about leave"}, {"role": "assistant", "content": "24 days [1]"}]
        self.rag.ask("And sick leave?", history=history)
        self.assertEqual(self.llm.last_messages[0]["content"], "Tell me about leave")
        self.assertIn("Question: And sick leave?", self.llm.last_messages[-1]["content"])
