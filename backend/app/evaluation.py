"""Retrieval evaluation metrics.

For each question we know a passage (evidence) that answers it. A retrieved chunk is relevant if it
contains that evidence.

- hit rate @k: share of questions where any of the top k chunks is relevant
- MRR (mean reciprocal rank): average of 1 / rank of the first relevant chunk (0 if none),
  so finding the answer at rank 1 scores 1.0 and at rank 2 scores 0.5
- precision @k: share of the top k chunks that are relevant
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from statistics import mean
from typing import Sequence

_SPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    return _SPACE.sub(" ", text).strip().lower()


def relevance(retrieved: Sequence[str], evidence: str) -> list[bool]:
    e = normalise(evidence)
    return [e in normalise(t) for t in retrieved]


def reciprocal_rank(flags: Sequence[bool]) -> float:
    for i, ok in enumerate(flags):
        if ok:
            return 1.0 / (i + 1)
    return 0.0


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile (p from 0 to 100)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, min(len(ordered), math.ceil(p / 100 * len(ordered))))
    return ordered[rank - 1]


@dataclass(frozen=True)
class RetrievalReport:
    questions: int
    k: int
    hit_rate: float
    mrr: float
    precision: float
    p50_ms: float
    p95_ms: float

    def row(self, label: str) -> str:
        return (f"| {label} | {self.k} | {self.hit_rate:.2f} | {self.mrr:.2f} | {self.precision:.2f} | "
                f"{self.p50_ms:.0f} | {self.p95_ms:.0f} |")


def summarise(all_flags: Sequence[Sequence[bool]], latencies_ms: Sequence[float], k: int) -> RetrievalReport:
    n = len(all_flags)
    return RetrievalReport(
        questions=n,
        k=k,
        hit_rate=sum(any(f[:k]) for f in all_flags) / n if n else 0.0,
        mrr=mean(reciprocal_rank(f[:k]) for f in all_flags) if n else 0.0,
        precision=mean(sum(f[:k]) / k for f in all_flags) if n else 0.0,
        p50_ms=percentile(latencies_ms, 50),
        p95_ms=percentile(latencies_ms, 95),
    )
