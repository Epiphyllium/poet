"""Small, dependency-free data structures shared by the system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Poem:
    title: str
    lines: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> Poem | None:
        if not isinstance(value, dict):
            return None
        title = value.get("title")
        lines = value.get("lines")
        if not isinstance(title, str) or not isinstance(lines, (list, tuple)):
            return None
        if not all(isinstance(line, str) for line in lines):
            return None
        return cls(title=title, lines=tuple(lines))

    def to_dict(self, original_topic: str) -> dict[str, object]:
        return {
            "topic": original_topic,
            "title": self.title,
            "lines": list(self.lines),
        }


@dataclass(frozen=True, slots=True)
class ValidationError:
    code: str
    message: str
    line_index: int | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    errors: tuple[ValidationError, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.errors
