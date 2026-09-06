"""Environment-based configuration with a tiny local .env loader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_local_env() -> None:
    project_env = Path(__file__).resolve().parents[2] / ".env"
    if not project_env.is_file():
        return
    for raw_line in project_env.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key:
            os.environ.setdefault(key, value)


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int
    candidate_count: int
    enable_repair: bool
    max_topic_chars: int
    tool_max_attempts: int = 4

    @classmethod
    def from_env(cls) -> Settings:
        _load_local_env()
        return cls(
            api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
            base_url=os.getenv(
                "OPENROUTER_BASE_URL",
                "https://openrouter.ai/api/v1/chat/completions",
            ).strip(),
            model=os.getenv(
                "POET_MODEL", "~deepseek/deepseek-v4-flash-latest"
            ).strip(),
            timeout_seconds=_int_env("POET_TIMEOUT_SECONDS", 8, 1, 60),
            candidate_count=_int_env("POET_CANDIDATE_COUNT", 4, 1, 8),
            enable_repair=_bool_env("POET_ENABLE_REPAIR", True),
            max_topic_chars=_int_env("POET_MAX_TOPIC_CHARS", 200, 1, 2000),
            tool_max_attempts=_int_env("POET_TOOL_MAX_ATTEMPTS", 4, 1, 6),
        )
