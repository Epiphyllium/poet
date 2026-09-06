"""OpenRouter client with structured output and a local validation tool loop."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections import Counter
from typing import Any

from .config import Settings
from .models import Poem, ValidationResult
from .prompts import SYSTEM_PROMPT, candidate_schema
from .rhyme import ending_chars_for, final_of, rhyme_guide
from .trace import record_event, record_usage
from .validator import validate_poem

logger = logging.getLogger(__name__)


class ModelClientError(RuntimeError):
    pass


def _poem_parameters() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "minLength": 2,
                "maxLength": 8,
                "description": "二至八个汉字的诗题",
            },
            "lines": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "description": "恰好四句，每句恰好五个汉字",
                "items": {"type": "string", "minLength": 5, "maxLength": 5},
            },
        },
        "required": ["title", "lines"],
        "additionalProperties": False,
    }


def _finals(poem: Poem) -> list[str | None]:
    return [final_of(line[-1]) if line else None for line in poem.lines]


def _choose_rhyme_target(
    finals: list[str | None], preferred: str | None = None
) -> str | None:
    if preferred:
        return preferred
    rhyme_finals = (
        [finals[index] for index in (0, 1, 3) if finals[index]]
        if len(finals) == 4
        else []
    )
    if not rhyme_finals:
        return None
    counts = Counter(rhyme_finals)
    first_seen = {value: rhyme_finals.index(value) for value in counts}
    return min(
        counts,
        key=lambda value: (
            -counts[value],
            -bool(ending_chars_for(value)),
            first_seen[value],
        ),
    )


def _tool_feedback(
    poem: Poem,
    validation: ValidationResult,
    preferred_rhyme_final: str | None = None,
) -> dict[str, object]:
    finals = _finals(poem)
    target = _choose_rhyme_target(finals, preferred_rhyme_final)
    suggested_chars = list(ending_chars_for(target))
    feedback_errors = [
        {
            "code": error.code,
            "line_index": error.line_index,
            "message": error.message,
        }
        for error in validation.errors
        if error.code not in {"rhyme_mismatch", "third_line_rhymes"}
    ]
    if len(finals) == 4 and target:
        for index in (0, 1, 3):
            if finals[index] != target:
                feedback_errors.append(
                    {
                        "code": "rhyme_mismatch",
                        "line_index": index,
                        "message": (
                            f"第{index + 1}句末字“{poem.lines[index][-1]}”的韵母是 "
                            f"{finals[index]}，正确目标韵母是 {target}"
                        ),
                    }
                )
        if finals[2] == target:
            feedback_errors.append(
                {
                    "code": "third_line_rhymes",
                    "line_index": 2,
                    "message": (
                        f"第3句末字“{poem.lines[2][-1]}”的韵母是 {target}，"
                        "但第三句必须转韵"
                    ),
                }
            )

    incorrect_indexes = {
        error["line_index"]
        for error in feedback_errors
        if error["line_index"] is not None
    }
    line_checks = []
    for index, line in enumerate(poem.lines):
        current_final = finals[index] if index < len(finals) else None
        is_turn_line = index == 2
        line_checks.append(
            {
                "line_number": index + 1,
                "text": line,
                "end_char": line[-1] if line else "",
                "final": current_final,
                "role": "转韵句" if is_turn_line else "押韵句",
                "expected": (
                    f"不得使用 {target} 韵"
                    if is_turn_line and target
                    else f"应使用 {target} 韵"
                    if target
                    else "等待确定目标韵"
                ),
                "status": "需修改" if index in incorrect_indexes else "正确",
            }
        )

    incorrect_lines = sorted(index + 1 for index in incorrect_indexes)
    preserve_lines = [
        index + 1 for index in range(len(poem.lines)) if index not in incorrect_indexes
    ]
    if validation.ok:
        instruction = "诗歌已通过全部硬约束"
    elif incorrect_lines:
        diagnoses = "；".join(
            str(error["message"])
            for error in feedback_errors
            if error["line_index"] is not None
        )
        line_label = "、".join(f"第{number}句" for number in incorrect_lines)
        preserve_label = "、".join(f"第{number}句" for number in preserve_lines)
        rhyme_hint = (
            f"目标韵母是 {target}，建议末字：{'、'.join(suggested_chars)}。"
            if suggested_chars
            else f"目标韵母是 {target}。" if target else ""
        )
        instruction = (
            f"{diagnoses}。只重写{line_label}，{preserve_label}保持原样。"
            f"{rhyme_hint}修改后必须提交完整的标题和四句诗。"
        )
    else:
        instruction = "请按照 errors 修复标题或整体格式，然后重新提交完整诗稿"

    return {
        "accepted": validation.ok,
        "finals": finals,
        "required_scheme": "第1、2、4句韵母相同；第3句韵母不同",
        "recommended_rhyme_final": target,
        "recommended_end_chars": suggested_chars,
        "target_rhyme": {
            "final": target,
            "suggested_end_chars": suggested_chars,
        },
        "incorrect_lines": incorrect_lines,
        "preserve_lines": preserve_lines,
        "line_checks": line_checks,
        "errors": feedback_errors,
        "instruction": instruction,
    }


class OpenRouterClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _post(self, payload: dict[str, Any], label: str) -> dict[str, Any]:
        if not self.settings.api_key:
            raise ModelClientError("OPENROUTER_API_KEY 未配置")
        request = urllib.request.Request(
            self.settings.base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
                "X-Title": "Five Character Poet",
            },
            method="POST",
        )
        logger.info(
            "[HTTP] %s POST %s model=%s key=<hidden>",
            label,
            self.settings.base_url,
            self.settings.model,
        )
        started = time.perf_counter()
        record_event(
            "model.request",
            "发送模型请求",
            {"label": label, "model": self.settings.model},
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.settings.timeout_seconds
            ) as response:
                body = response.read().decode("utf-8")
                logger.info(
                    "[HTTP] %s status=%s response_bytes=%d",
                    label,
                    getattr(response, "status", 200),
                    len(body.encode("utf-8")),
                )
        except urllib.error.HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace")
            record_event(
                "model.error",
                "模型请求失败",
                {"label": label, "status": exc.code, "error": detail},
            )
            raise ModelClientError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            record_event(
                "model.error",
                "模型请求失败",
                {"label": label, "error": str(exc)},
            )
            raise ModelClientError(f"OpenRouter 请求失败: {exc}") from exc

        try:
            result = json.loads(body)
            choice = result["choices"][0]
            logger.info(
                "[HTTP响应] %s finish_reason=%s usage=%s",
                label,
                choice.get("finish_reason"),
                result.get("usage"),
            )
            usage = result.get("usage")
            record_usage(usage)
            record_event(
                "model.response",
                "收到模型响应",
                {
                    "label": label,
                    "finish_reason": choice.get("finish_reason"),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "usage": usage or {},
                },
            )
            return result
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ModelClientError("OpenRouter 响应结构无法识别") from exc

    def complete(self, user_prompt: str, candidate_count: int) -> str:
        """Legacy structured-output path retained for injectable test clients."""

        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.85,
            "max_tokens": 1200,
            "reasoning": {"enabled": False},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "poem_candidates",
                    "strict": True,
                    "schema": candidate_schema(candidate_count),
                },
            },
            "provider": {"require_parameters": True},
        }
        result = self._post(payload, "structured-output")
        choice = result["choices"][0]
        message = choice["message"]
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
            if text.strip():
                return text
        refusal = message.get("refusal")
        finish_reason = choice.get("finish_reason", "unknown")
        raise ModelClientError(
            f"模型没有返回文本内容: {refusal or 'empty'} "
            f"(finish_reason={finish_reason})"
        )

    def generate_poem_with_tool(self, topic: str, max_attempts: int) -> Poem | None:
        """Let the model submit poems to the deterministic validator tool."""

        tool = {
            "type": "function",
            "function": {
                "name": "submit_poem",
                "description": (
                    "提交一首候选五言古诗给本地程序。程序会计算真实普通话韵母并检查格式。"
                    "未通过时必须依据工具返回的 finals 和 errors 修改后再次提交。"
                ),
                "strict": True,
                "parameters": _poem_parameters(),
            },
        }
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"主题：{topic or '未名之思'}\n"
                    "创作一首切题、连贯、有古典意境的五言诗。"
                    "必须调用 submit_poem 提交；若工具指出错误，修改后再次调用。\n"
                    f"严格同韵字参考组：{rhyme_guide()}。"
                    "第1、2、4句应从同一组各选一个字收尾，第3句不得使用该组。"
                ),
            },
        ]

        preferred_rhyme_final: str | None = None
        for attempt in range(1, max_attempts + 1):
            logger.info("[工具循环] attempt=%d/%d", attempt, max_attempts)
            record_event(
                "tool.attempt",
                f"第 {attempt} 次提交",
                {"attempt": attempt, "max_attempts": max_attempts},
            )
            payload: dict[str, Any] = {
                "model": self.settings.model,
                "messages": messages,
                "tools": [tool],
                "tool_choice": {
                    "type": "function",
                    "function": {"name": "submit_poem"},
                },
                "parallel_tool_calls": False,
                "temperature": 0.8,
                "max_tokens": 900,
                "reasoning": {"enabled": False},
                "provider": {"require_parameters": True},
            }
            result = self._post(payload, f"tool-attempt-{attempt}")
            message = result["choices"][0]["message"]
            tool_calls = message.get("tool_calls")
            logger.info("[工具调用] raw=%s", tool_calls)
            if not isinstance(tool_calls, list) or not tool_calls:
                raise ModelClientError("模型未调用 submit_poem")

            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content"),
                    "tool_calls": tool_calls,
                }
            )
            for call in tool_calls:
                call_id = str(call.get("id", f"submit-{attempt}"))
                function = call.get("function", {})
                try:
                    arguments = function.get("arguments", "{}")
                    value = (
                        json.loads(arguments)
                        if isinstance(arguments, str)
                        else arguments
                    )
                    poem = Poem.from_mapping(value)
                except (TypeError, json.JSONDecodeError):
                    poem = None

                if poem is None:
                    feedback: dict[str, object] = {
                        "accepted": False,
                        "errors": [
                            {
                                "code": "invalid_arguments",
                                "message": "工具参数无法解析",
                            }
                        ],
                        "instruction": "请重新调用 submit_poem 并提供 title 和四句 lines",
                    }
                else:
                    validation = validate_poem(poem)
                    feedback = _tool_feedback(
                        poem, validation, preferred_rhyme_final
                    )
                    if preferred_rhyme_final is None:
                        value = feedback.get("recommended_rhyme_final")
                        preferred_rhyme_final = value if isinstance(value, str) else None
                    logger.info(
                        "[工具执行] poem=%s feedback=%s",
                        poem,
                        feedback,
                    )
                    record_event(
                        "tool.result",
                        "校验诗稿",
                        {
                            "attempt": attempt,
                            "poem": {
                                "title": poem.title,
                                "lines": list(poem.lines),
                            },
                            "feedback": feedback,
                        },
                    )
                    if validation.ok:
                        logger.info(
                            "[工具接受] attempt=%d title=%s", attempt, poem.title
                        )
                        return poem

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": "submit_poem",
                        "content": json.dumps(feedback, ensure_ascii=False),
                    }
                )

        logger.info("[工具循环结束] %d 次提交均未通过", max_attempts)
        return None
