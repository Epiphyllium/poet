"""Network-free, prevalidated fallback selection."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from importlib.resources import files

from .models import Poem
from .validator import validate_poem

logger = logging.getLogger(__name__)

EMERGENCY_POEM = Poem(
    title="山中晚思",
    lines=("山雨洗浮尘", "幽径少行人", "松风鸣石涧", "白云伴此身"),
)


@lru_cache(maxsize=1)
def _catalog() -> tuple[dict[str, tuple[str, ...]], dict[str, Poem]]:
    data_dir = files("poet").joinpath("data")
    themes_raw = json.loads(data_dir.joinpath("themes.json").read_text(encoding="utf-8"))
    poems_raw = json.loads(data_dir.joinpath("poems.json").read_text(encoding="utf-8"))
    themes = {name: tuple(str(word).casefold() for word in words) for name, words in themes_raw.items()}
    poems = {name: Poem.from_mapping(value) for name, value in poems_raw.items()}
    if any(poem is None for poem in poems.values()):
        raise ValueError("兜底诗库结构不合法")
    typed_poems = {name: poem for name, poem in poems.items() if poem is not None}
    invalid = [name for name, poem in typed_poems.items() if not validate_poem(poem).ok]
    if invalid:
        raise ValueError(f"兜底诗未通过校验: {', '.join(invalid)}")
    return themes, typed_poems


def fallback_poem(topic: str) -> Poem:
    """Choose the most specific known theme, with a literal final safety net."""

    try:
        themes, poems = _catalog()
        folded = topic.casefold()
        best_name = "default"
        best_score = 0
        for name, keywords in themes.items():
            matches = [keyword for keyword in keywords if keyword and keyword in folded]
            score = sum(
                len(keyword) + (2 if keyword.isascii() else 0)
                for keyword in matches
            )
            if score > best_score:
                best_name, best_score = name, score
        logger.info(
            "[主题匹配] topic=%r theme=%s score=%d",
            topic,
            best_name,
            best_score,
        )
        return poems.get(best_name, poems["default"])
    except Exception as exc:
        logger.info("[主题匹配失败] %s", exc)
        return EMERGENCY_POEM
