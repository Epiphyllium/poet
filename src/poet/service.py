"""Public orchestration with a deterministic final safety path."""

from __future__ import annotations

import logging
from typing import Protocol

from .config import Settings
from .fallback import EMERGENCY_POEM, fallback_poem
from .models import Poem
from .parser import parse_candidates
from .prompts import generation_prompt, repair_prompt
from .scorer import rank_candidates, score_poem
from .trace import record_event, set_result, trace_session
from .validator import validate_poem

logger = logging.getLogger(__name__)


class ModelClient(Protocol):
    def complete(self, user_prompt: str, candidate_count: int) -> str: ...


def _safe_topic(value: object, limit: int) -> tuple[str, str]:
    original = value if isinstance(value, str) else "" if value is None else str(value)
    prompt_topic = " ".join(original.split())[:limit]
    return original, prompt_topic


def _generate_with_client(
    topic: object, settings: Settings, client: ModelClient | None
) -> dict[str, object]:
    original_topic, prompt_topic = _safe_topic(topic, settings.max_topic_chars)
    candidates: list[Poem] = []
    tool_mode = False
    logger.info("[输入] original_topic=%r", original_topic)
    logger.info("[输入] prompt_topic=%r", prompt_topic)
    logger.info(
        "[配置] model=%s candidates=%d repair=%s tool_attempts=%d timeout=%ss api_key_configured=%s",
        settings.model,
        settings.candidate_count,
        settings.enable_repair,
        settings.tool_max_attempts,
        settings.timeout_seconds,
        bool(settings.api_key),
    )
    record_event(
        "input.ready",
        "主题已整理",
        {"original_topic": original_topic, "prompt_topic": prompt_topic},
    )

    if client is not None:
        tool_generator = getattr(client, "generate_poem_with_tool", None)
        if callable(tool_generator):
            tool_mode = True
            logger.info("[生成模式] submit_poem 工具循环")
            record_event(
                "generation.mode",
                "进入工具生成",
                {"max_attempts": settings.tool_max_attempts},
            )
            try:
                poem = tool_generator(prompt_topic, settings.tool_max_attempts)
                if poem is not None:
                    candidates = [poem]
                logger.info("[工具结果] candidates=%d", len(candidates))
            except Exception as exc:
                logger.info("[工具生成失败] %s", exc)
                record_event(
                    "generation.error", "工具生成失败", {"error": str(exc)}
                )
        else:
            prompt = generation_prompt(prompt_topic, settings.candidate_count)
            logger.info("[生成模式] 结构化多候选")
            logger.info("[生成] prompt=%s", prompt)
            try:
                response = client.complete(
                    prompt,
                    settings.candidate_count,
                )
                logger.info("[生成] raw_response=%s", response)
                candidates = parse_candidates(response)
                logger.info("[解析] candidates=%d", len(candidates))
            except Exception as exc:
                logger.info("[生成失败] %s", exc)
    else:
        logger.info("[生成跳过] API Key 未配置，直接使用本地兜底")

    valid: list[Poem] = []
    for index, poem in enumerate(candidates, start=1):
        validation = validate_poem(poem)
        if validation.ok:
            valid.append(poem)
            logger.info(
                "[校验] candidate=%d valid=true score=%.2f poem=%s",
                index,
                score_poem(prompt_topic, poem),
                poem,
            )
            record_event(
                "candidate.valid",
                "候选通过校验",
                {
                    "candidate": index,
                    "title": poem.title,
                    "score": score_poem(prompt_topic, poem),
                },
            )
        else:
            logger.info(
                "[校验] candidate=%d valid=false errors=%s poem=%s",
                index,
                [
                    {
                        "code": error.code,
                        "line_index": error.line_index,
                        "message": error.message,
                    }
                    for error in validation.errors
                ],
                poem,
            )
            record_event(
                "candidate.invalid",
                "候选未通过校验",
                {
                    "candidate": index,
                    "title": poem.title,
                    "errors": [error.code for error in validation.errors],
                },
            )
    if valid:
        chosen = rank_candidates(prompt_topic, valid)[0]
        logger.info(
            "[选择] 使用模型候选 title=%s score=%.2f",
            chosen.title,
            score_poem(prompt_topic, chosen),
        )
        result = chosen.to_dict(original_topic)
        set_result(result, "model")
        record_event("result.selected", "采用模型诗作", {"title": chosen.title})
        logger.info("[最终输出] %s", result)
        return result

    if client is not None and not tool_mode and settings.enable_repair and candidates:
        best = min(candidates, key=lambda poem: len(validate_poem(poem).errors))
        validation = validate_poem(best)
        prompt = repair_prompt(prompt_topic, best, validation)
        logger.info("[修复] selected=%s", best)
        logger.info("[修复] prompt=%s", prompt)
        try:
            response = client.complete(prompt, 1)
            logger.info("[修复] raw_response=%s", response)
            repaired = parse_candidates(response)
            logger.info("[修复解析] candidates=%d", len(repaired))
            repaired_valid: list[Poem] = []
            for index, poem in enumerate(repaired, start=1):
                repaired_validation = validate_poem(poem)
                logger.info(
                    "[修复校验] candidate=%d valid=%s errors=%s poem=%s",
                    index,
                    repaired_validation.ok,
                    [error.code for error in repaired_validation.errors],
                    poem,
                )
                if repaired_validation.ok:
                    repaired_valid.append(poem)
            if repaired_valid:
                chosen = rank_candidates(prompt_topic, repaired_valid)[0]
                logger.info("[选择] 使用修复候选 title=%s", chosen.title)
                result = chosen.to_dict(original_topic)
                set_result(result, "repair")
                record_event(
                    "result.selected", "采用修复诗作", {"title": chosen.title}
                )
                logger.info("[最终输出] %s", result)
                return result
        except Exception as exc:
            logger.info("[修复失败] %s", exc)
    elif tool_mode:
        logger.info("[旧修复跳过] 工具循环已包含逐轮校验与修复")
    elif not candidates:
        logger.info("[修复跳过] 没有可修复候选")
    elif not settings.enable_repair:
        logger.info("[修复跳过] 修复功能已关闭")

    poem = fallback_poem(prompt_topic)
    logger.info("[兜底] selected_title=%s poem=%s", poem.title, poem)
    if not validate_poem(poem).ok:
        logger.info("[兜底异常] 主题兜底未通过校验，切换紧急兜底")
        poem = EMERGENCY_POEM
    result = poem.to_dict(original_topic)
    source = "emergency" if poem is EMERGENCY_POEM else "fallback"
    set_result(result, source)
    record_event(
        "result.fallback",
        "采用本地兜底",
        {"title": poem.title, "source": source},
    )
    logger.info("[最终输出] %s", result)
    return result


def generate_poem(topic: str) -> dict[str, object]:
    original_topic = topic if isinstance(topic, str) else "" if topic is None else str(topic)
    try:
        settings = Settings.from_env()
        with trace_session(original_topic, settings.model):
            try:
                client: ModelClient | None = None
                if settings.api_key:
                    from .llm import OpenRouterClient

                    client = OpenRouterClient(settings)
                return _generate_with_client(topic, settings, client)
            except Exception as exc:
                logger.exception("Unexpected poem service failure; using emergency poem")
                result = EMERGENCY_POEM.to_dict(original_topic)
                set_result(result, "emergency")
                record_event(
                    "result.emergency",
                    "内部异常后采用紧急兜底",
                    {"error": str(exc)},
                )
                return result
    except Exception:
        # This boundary is deliberately last-resort: callers always receive the
        # documented shape even if configuration or an internal helper fails.
        logger.exception("Unexpected poem service failure; using emergency poem")
        return EMERGENCY_POEM.to_dict(original_topic)
