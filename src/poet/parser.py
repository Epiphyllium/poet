"""Best-effort candidate extraction; validation remains authoritative."""

from __future__ import annotations

import json
import re
from typing import Any, Iterator

from .models import Poem

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)
_LINE_PREFIX_RE = re.compile(r"^\s*(?:标题\s*[：:]|[一二三四1-4][、.．]\s*)")


def _json_values(text: str) -> Iterator[Any]:
    cleaned = _FENCE_RE.sub("", text.strip())
    seen: set[str] = set()
    try:
        value = json.loads(cleaned)
        marker = repr(value)
        seen.add(marker)
        yield value
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        marker = repr(value)
        if marker not in seen:
            seen.add(marker)
            yield value


def _poems_from_value(value: Any) -> Iterator[Poem]:
    if isinstance(value, dict) and isinstance(value.get("candidates"), list):
        for item in value["candidates"]:
            poem = Poem.from_mapping(item)
            if poem is not None:
                yield poem
        return
    poem = Poem.from_mapping(value)
    if poem is not None:
        yield poem
        return
    if isinstance(value, list):
        for item in value:
            poem = Poem.from_mapping(item)
            if poem is not None:
                yield poem


def _plain_text_poem(text: str) -> Poem | None:
    rows = [row.strip() for row in text.splitlines() if row.strip()]
    rows = [_LINE_PREFIX_RE.sub("", row).strip() for row in rows]
    if len(rows) == 5:
        return Poem(title=rows[0], lines=tuple(rows[1:]))
    return None


def parse_candidates(text: str) -> list[Poem]:
    if not isinstance(text, str) or not text.strip():
        return []
    poems: list[Poem] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for value in _json_values(text):
        for poem in _poems_from_value(value):
            marker = (poem.title, poem.lines)
            if marker not in seen:
                seen.add(marker)
                poems.append(poem)
    if not poems:
        poem = _plain_text_poem(text)
        if poem is not None:
            poems.append(poem)
    return poems
