import unittest

from app.context import approx_tokens, is_near_duplicate, select_sources
from app.models import Chunk, Hit
from app.prompts import NOT_FOUND, SYSTEM_PROMPT, build_messages, cited_numbers


def hit(i: int, text: str, score: float, page: int = 1) -> Hit:
    return Hit(Chunk(f"d-{i}", "d", "file.pdf", page, i, text), score)


class SelectSourcesTest(unittest.TestCase):
    def test_drops_weak_matches_and_numbers_the_rest_best_first(self):
        hits = [hit(1, "leave policy details here", 0.31), hit(2, "annual leave is 24 days", 0.82), hit(3, "unrelated text", 0.10)]
        sources = select_sources(hits, min_score=0.3, token_budget=1000)
        self.assertEqual([s.text for s in sources], ["annual leave is 24 days", "leave policy details here"])
        self.assertEqual([s.number for s in sources], [1, 2])

    def test_skips_near_duplicates_from_chunk_overlap(self):
        a = "Every employee receives 24 days of paid annual leave per calendar year in addition to holidays"
        b = "Every employee receives 24 days of paid annual leave per calendar year in addition to public holidays"
        sources = select_sources([hit(1, a, 0.9), hit(2, b, 0.89), hit(3, "Sick leave is separate", 0.5)], 0.2, 1000)
        self.assertEqual(len(sources), 2)
        self.assertTrue(is_near_duplicate(b, [a]))

    def test_stays_within_the_token_budget_but_always_keeps_the_best(self):
        long = "word " * 400   # ~500 tokens
        sources = select_sources([hit(1, long, 0.9), hit(2, long + "x", 0.8), hit(3, "short one", 0.7)], 0.2, token_budget=520)
        self.assertEqual([s.number for s in sources], [1, 2])
        self.assertEqual(sources[1].text, "short one")
        only = select_sources([hit(1, long, 0.9)], 0.2, token_budget=10)
        self.assertEqual(len(only), 1)

    def test_approx_tokens(self):
        self.assertEqual(approx_tokens("abcd" * 10), 10)
        self.assertEqual(approx_tokens(""), 1)


class PromptTest(unittest.TestCase):
    def test_prompt_contains_numbered_sources_and_the_question(self):
        sources = select_sources([hit(1, "Annual leave is 24 days.", 0.9, page=2)], 0.2, 1000)
        messages = build_messages("How much leave?", sources)
        self.assertEqual(len(messages), 1)
        content = messages[0]["content"]
        self.assertIn("[1] file.pdf, page 2\nAnnual leave is 24 days.", content)
        self.assertTrue(content.endswith("Question: How much leave?"))

    def test_history_is_trimmed_and_starts_with_a_user_turn(self):
        history = [{"role": "assistant", "content": "hi"}] + [
            {"role": r, "content": f"m{i}"} for i, r in enumerate(["user", "assistant"] * 4)]
        messages = build_messages("next?", [], history)
        self.assertEqual(messages[0]["role"], "user")
        self.assertLessEqual(len(messages), 5)
        self.assertEqual(messages[-1]["role"], "user")

    def test_cited_numbers_ignores_unknown_and_repeated_citations(self):
        self.assertEqual(cited_numbers("A [2]. B [1][2]. C [9].", 3), [2, 1])

    def test_system_prompt_forbids_outside_knowledge_and_names_the_refusal(self):
        self.assertIn("ONLY the numbered sources", SYSTEM_PROMPT)
        self.assertIn(NOT_FOUND, SYSTEM_PROMPT)
        self.assertIn("not instructions", SYSTEM_PROMPT)
