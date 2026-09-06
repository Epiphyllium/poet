"""Thread-safe in-memory traces for local development and UI inspection."""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(slots=True)
class TraceEvent:
    at_ms: float
    kind: str
    title: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "at_ms": round(self.at_ms, 1),
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
        }


@dataclass(slots=True)
class TraceRun:
    id: str
    topic: str
    model: str
    started_at: str
    _started_clock: float
    status: str = "running"
    source: str = "pending"
    duration_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    result: dict[str, Any] | None = None
    events: list[TraceEvent] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "model": self.model,
            "started_at": self.started_at,
            "status": self.status,
            "source": self.source,
            "duration_ms": round(self.duration_ms, 1),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "title": self.result.get("title") if self.result else None,
            "event_count": len(self.events),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.summary(),
            "result": self.result,
            "events": [event.to_dict() for event in self.events],
        }


class TraceStore:
    def __init__(self, max_runs: int = 100):
        self._runs: deque[TraceRun] = deque(maxlen=max_runs)
        self._lock = threading.RLock()

    def add(self, run: TraceRun) -> None:
        with self._lock:
            self._runs.appendleft(run)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [run.summary() for run in self._runs]

    def get(self, trace_id: str) -> dict[str, Any] | None:
        with self._lock:
            for run in self._runs:
                if run.id == trace_id:
                    return run.to_dict()
        return None


STORE = TraceStore()
_CURRENT: ContextVar[TraceRun | None] = ContextVar("poet_trace", default=None)
_LAST_ID: ContextVar[str | None] = ContextVar("poet_last_trace_id", default=None)


@contextmanager
def trace_session(topic: str, model: str) -> Iterator[TraceRun]:
    run = TraceRun(
        id=uuid.uuid4().hex[:12],
        topic=topic,
        model=model,
        started_at=_utc_now(),
        _started_clock=time.perf_counter(),
    )
    STORE.add(run)
    token = _CURRENT.set(run)
    record_event("run.start", "开始生成", {"topic": topic, "model": model})
    try:
        yield run
        if run.status == "running":
            run.status = "completed"
    except Exception:
        run.status = "error"
        record_event("run.error", "生成异常")
        raise
    finally:
        run.duration_ms = (time.perf_counter() - run._started_clock) * 1000
        record_event(
            "run.finish",
            "生成结束",
            {"status": run.status, "duration_ms": round(run.duration_ms, 1)},
        )
        _LAST_ID.set(run.id)
        _CURRENT.reset(token)


def record_event(kind: str, title: str, detail: dict[str, Any] | None = None) -> None:
    run = _CURRENT.get()
    if run is None:
        return
    run.events.append(
        TraceEvent(
            at_ms=(time.perf_counter() - run._started_clock) * 1000,
            kind=kind,
            title=title,
            detail=detail or {},
        )
    )


def record_usage(usage: dict[str, Any] | None) -> None:
    run = _CURRENT.get()
    if run is None or not isinstance(usage, dict):
        return
    run.prompt_tokens += int(usage.get("prompt_tokens") or 0)
    run.completion_tokens += int(usage.get("completion_tokens") or 0)
    run.total_tokens += int(usage.get("total_tokens") or 0)
    run.cost += float(usage.get("cost") or 0.0)


def set_result(result: dict[str, Any], source: str) -> None:
    run = _CURRENT.get()
    if run is None:
        return
    run.result = result
    run.source = source


def last_trace_id() -> str | None:
    return _LAST_ID.get()


def list_traces() -> list[dict[str, Any]]:
    return STORE.list()


def get_trace(trace_id: str) -> dict[str, Any] | None:
    return STORE.get(trace_id)
