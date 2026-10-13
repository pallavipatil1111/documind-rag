"""Context window optimisation: which retrieved chunks go into the prompt.

1. Drop weak matches below a cosine-similarity threshold. Irrelevant context makes answers worse
   and costs tokens.
2. Drop near-duplicates (chunk overlap means neighbouring chunks repeat text).
3. Add chunks best-first until a token budget is reached, so the prompt stays a predictable size
   however long the documents are.
"""
from __future__ import annotations

import re
from typing import Callable, Sequence

from .models import Hit, Source

_WORD = re.compile(r"\w+")


def approx_tokens(text: str) -> int:
    """About 4 characters per token for English; used when tiktoken isn't installed."""
    return max(1, len(text) // 4)


def token_counter() -> Callable[[str], int]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return lambda text: len(enc.encode(text))
    except Exception:  # noqa: BLE001 - optional dependency
        return approx_tokens


def _words(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def is_near_duplicate(text: str, kept: Sequence[str], threshold: float = 0.8) -> bool:
    """True if the text shares at least `threshold` of its words (Jaccard) with a chunk already kept."""
    w = _words(text)
    for other in kept:
        o = _words(other)
        if w and o and len(w & o) / len(w | o) >= threshold:
            return True
    return False


def select_sources(hits: Sequence[Hit], min_score: float, token_budget: int,
                   count_tokens: Callable[[str], int] = approx_tokens) -> list[Source]:
    chosen: list[Hit] = []
    used = 0
    for hit in sorted(hits, key=lambda h: -h.score):
        if hit.score < min_score:
            continue
        if is_near_duplicate(hit.chunk.text, [c.chunk.text for c in chosen]):
            continue
        cost = count_tokens(hit.chunk.text)
        if chosen and used + cost > token_budget:
            continue
        chosen.append(hit)
        used += cost
    return [Source(i + 1, h.chunk.doc_id, h.chunk.filename, h.chunk.page, h.chunk.text, round(h.score, 4))
            for i, h in enumerate(chosen)]
