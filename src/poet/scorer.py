"""Cheap deterministic ranking for candidates that already pass validation."""

from __future__ import annotations

from collections import Counter

from .models import Poem


def score_poem(topic: str, poem: Poem) -> float:
    text = poem.title + "".join(poem.lines)
    topic_han = {char for char in topic if "\u4e00" <= char <= "\u9fff"}
    overlap = sum(1 for char in topic_han if char in text)

    counts = Counter(text)
    repetition = sum(count - 2 for count in counts.values() if count > 2)
    repeated_lines = 4 - len(set(poem.lines))
    return overlap * 3.0 - repetition * 1.5 - repeated_lines * 5.0


def rank_candidates(topic: str, poems: list[Poem]) -> list[Poem]:
    return sorted(poems, key=lambda poem: score_poem(topic, poem), reverse=True)
