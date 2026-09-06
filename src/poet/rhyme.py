"""Mandarin final extraction for the challenge's exact-rhyme rule."""

from __future__ import annotations

import re

from pypinyin import Style, lazy_pinyin

_FINAL_RE = re.compile(r"^[a-zv]+$")

_ENDING_CHAR_BANK: dict[str, tuple[str, ...]] = {
    "an": ("山", "寒", "安", "残", "难", "栏"),
    "ang": ("堂", "苍", "茫", "藏", "航", "商", "章"),
    "iang": ("江", "香", "乡", "阳", "凉", "墙", "央"),
    "uang": ("光", "霜", "窗", "床", "黄", "荒", "望"),
    "en": ("门", "痕", "尘", "人", "深", "身", "根"),
    "eng": ("灯", "城", "声", "生", "冷", "梦", "风"),
    "ing": ("明", "清", "星", "庭", "影", "冰", "醒"),
    "ong": ("空", "钟", "松", "鸿", "中", "东", "红"),
    "ou": ("楼", "愁", "洲", "头", "舟", "侯"),
    "iou": ("秋", "流", "幽", "游", "愁"),
    "uei": ("归", "晖", "微", "辉", "飞"),
}


def normalize_final(value: str) -> str:
    """Normalize alternate spellings without broadening rhyme categories."""

    return value.lower().replace("ü", "v").replace("u:", "v")


def final_of(char: str) -> str | None:
    """Return a tone-free strict pinyin final, or ``None`` if unavailable."""

    if not isinstance(char, str) or len(char) != 1:
        return None
    values = lazy_pinyin(
        char,
        style=Style.FINALS,
        strict=True,
        neutral_tone_with_five=False,
        errors=lambda _: [],
    )
    if len(values) != 1:
        return None
    value = normalize_final(values[0])
    return value if value and _FINAL_RE.fullmatch(value) else None


def rhymes(left: str, right: str) -> bool:
    left_final = final_of(left)
    right_final = final_of(right)
    return left_final is not None and left_final == right_final


def ending_chars_for(final: str | None) -> tuple[str, ...]:
    """Return only bank characters verified by the same production extractor."""

    if final is None:
        return ()
    return tuple(
        char for char in _ENDING_CHAR_BANK.get(final, ()) if final_of(char) == final
    )


def rhyme_guide() -> str:
    groups = []
    for final in ("en", "ing", "ong", "an", "ou", "iang", "uang", "ang"):
        chars = ending_chars_for(final)
        if chars:
            groups.append(f"{final}:{''.join(chars)}")
    return "；".join(groups)
