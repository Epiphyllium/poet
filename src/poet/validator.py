"""Deterministic validation of every hard output constraint."""

from __future__ import annotations

from typing import Any

from .models import Poem, ValidationError, ValidationResult
from .rhyme import final_of


def is_han_text(value: str) -> bool:
    """Accept common CJK ideographs, Extension A and compatibility forms."""

    return bool(value) and all(
        "\u3400" <= char <= "\u4dbf"
        or "\u4e00" <= char <= "\u9fff"
        or "\uf900" <= char <= "\ufaff"
        for char in value
    )


def validate_poem(value: Any) -> ValidationResult:
    poem = value if isinstance(value, Poem) else Poem.from_mapping(value)
    if poem is None:
        return ValidationResult(
            (ValidationError("invalid_shape", "诗歌必须包含字符串 title 和字符串数组 lines"),)
        )

    errors: list[ValidationError] = []
    if not 2 <= len(poem.title) <= 8:
        errors.append(ValidationError("title_length", "标题必须为二至八个汉字"))
    if not is_han_text(poem.title):
        errors.append(ValidationError("title_chars", "标题只能包含汉字"))

    if len(poem.lines) != 4:
        errors.append(ValidationError("line_count", "诗句必须恰好为四句"))

    for index, line in enumerate(poem.lines):
        if len(line) != 5:
            errors.append(
                ValidationError("line_length", "每句必须恰好为五个汉字", index)
            )
        if not is_han_text(line):
            errors.append(
                ValidationError("line_chars", "诗句只能包含汉字", index)
            )

    if len(poem.lines) == 4 and all(poem.lines):
        finals = [final_of(line[-1]) for line in poem.lines]
        if any(value is None for value in finals):
            errors.append(ValidationError("rhyme_unknown", "无法取得韵脚的普通话韵母"))
        else:
            first_final = finals[0]
            for index in (1, 3):
                if finals[index] != first_final:
                    errors.append(
                        ValidationError(
                            "rhyme_mismatch",
                            f"第{index + 1}句韵母 {finals[index]} 与第一句韵母 {first_final} 不同",
                            index,
                        )
                    )
            if finals[2] == first_final:
                errors.append(
                    ValidationError(
                        "third_line_rhymes",
                        "第三句应转韵，不能与第一二四句押同一韵",
                        2,
                    )
                )

    return ValidationResult(tuple(errors))
