import unittest

from app.evaluation import percentile, reciprocal_rank, relevance, summarise


class EvaluationTest(unittest.TestCase):
    def test_relevance_ignores_case_and_line_breaks(self):
        self.assertEqual(relevance(["Annual\nleave is 24 DAYS", "other"], "leave is 24 days"), [True, False])

    def test_reciprocal_rank(self):
        self.assertEqual(reciprocal_rank([False, True, True]), 0.5)
        self.assertEqual(reciprocal_rank([False, False]), 0.0)

    def test_summary_metrics(self):
        flags = [[True, False, False], [False, False, True], [False, False, False], [False, True, False]]
        r = summarise(flags, [10, 20, 30, 40], k=3)
        self.assertEqual(r.hit_rate, 0.75)
        self.assertAlmostEqual(r.mrr, (1 + 1 / 3 + 0 + 0.5) / 4)
        self.assertAlmostEqual(r.precision, 3 / 12)
        self.assertEqual(summarise(flags, [1, 2, 3, 4], k=1).hit_rate, 0.25)

    def test_percentiles(self):
        self.assertEqual(percentile([5, 1, 3, 2, 4], 50), 3)
        self.assertEqual(percentile(list(range(1, 101)), 95), 95)
        self.assertEqual(percentile([], 50), 0.0)
