import io
import unittest

from app import pdf
from app.chunking import chunk_id, chunk_pages, doc_id_for
from app.models import Page
from tests.helpers import SAMPLE, SimpleSplitter


class PdfTest(unittest.TestCase):
    def test_reads_every_page_with_its_number(self):
        pages = pdf.read_pages(SAMPLE.read_bytes(), max_pages=50)
        self.assertEqual([p.number for p in pages], [1, 2, 3, 4, 5, 6])
        self.assertIn("24 days of paid annual leave", " ".join(pages[1].text.split()))

    def test_rejects_files_that_are_not_pdfs(self):
        with self.assertRaises(pdf.PdfError):
            pdf.read_pages(b"hello, not a pdf", max_pages=50)

    def test_rejects_pdfs_over_the_page_limit(self):
        with self.assertRaisesRegex(pdf.PdfError, "limit is 3"):
            pdf.read_pages(SAMPLE.read_bytes(), max_pages=3)

    def test_rejects_pdfs_without_text(self):
        from pypdf import PdfWriter

        w = PdfWriter()
        w.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        w.write(buf)
        with self.assertRaisesRegex(pdf.PdfError, "No text"):
            pdf.read_pages(buf.getvalue(), max_pages=50)

    def test_clean_joins_hyphenated_words_and_collapses_spaces(self):
        self.assertEqual(pdf.clean("retrie-\nval   augmented\n\n\n\ngeneration"), "retrieval augmented\n\ngeneration")


class ChunkingTest(unittest.TestCase):
    def test_chunks_keep_page_numbers_and_get_stable_ids(self):
        pages = [Page(1, "First page sentence one is here. " * 20), Page(2, "Second page text is a little different. " * 20)]
        chunks = chunk_pages(pages, "doc1", "a.pdf", SimpleSplitter(size=200, overlap=40))
        self.assertGreater(len(chunks), 4)
        self.assertEqual(chunks[0].id, chunk_id("doc1", 0))
        self.assertEqual([c.index for c in chunks], list(range(len(chunks))))
        self.assertEqual({c.page for c in chunks}, {1, 2})
        self.assertTrue(all(len(c.text) <= 200 for c in chunks))

    def test_tiny_fragments_are_dropped(self):
        chunks = chunk_pages([Page(1, "12")], "d", "a.pdf", SimpleSplitter())
        self.assertEqual(chunks, [])

    def test_same_file_same_document_id(self):
        self.assertEqual(doc_id_for(b"abc"), doc_id_for(b"abc"))
        self.assertNotEqual(doc_id_for(b"abc"), doc_id_for(b"abd"))
