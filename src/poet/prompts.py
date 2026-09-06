"""Prompts and response schemas kept out of orchestration code."""

from __future__ import annotations

import json

from .models import Poem, ValidationResult

SYSTEM_PROMPT = """你是一位擅长古典汉语的五言诗人。你的任务是围绕用户主题创作四句五言古诗。
必须严格遵守：标题二至八个汉字；恰好四句；每句恰好五个汉字；标题和诗句只含汉字；第一句、第二句、第四句末字的普通话韵母必须完全相同并忽略声调；第三句末字必须使用不同韵母，不押该韵。
避免现代词汇直译，将现代主题转化为古典意象。四句应有起承转合、场景统一、用词自然，候选之间不要只是替换一两个字。仅按给定结构返回数据。"""


def candidate_schema(count: int) -> dict[str, object]:
    poem_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "minLength": 2,
                "maxLength": 8,
                "pattern": "^[\\u3400-\\u4dbf\\u4e00-\\u9fff\\uf900-\\ufaff]+$",
            },
            "lines": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "string",
                    "minLength": 5,
                    "maxLength": 5,
                    "pattern": "^[\\u3400-\\u4dbf\\u4e00-\\u9fff\\uf900-\\ufaff]{5}$",
                },
            },
        },
        "required": ["title", "lines"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "candidates": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": poem_schema,
            }
        },
        "required": ["candidates"],
        "additionalProperties": False,
    }


def generation_prompt(topic: str, count: int) -> str:
    return (
        f"主题：{topic or '未名之思'}\n"
        f"请创作 {count} 首彼此不同的候选五言古诗。"
        "先在心中逐字计数，核对第一二四句同韵且第三句不押该韵，再按结构返回。"
    )


def repair_prompt(topic: str, poem: Poem, result: ValidationResult) -> str:
    errors = [error.message for error in result.errors]
    source = json.dumps(
        {"title": poem.title, "lines": list(poem.lines)}, ensure_ascii=False
    )
    return (
        f"主题：{topic or '未名之思'}\n"
        f"待修复诗歌：{source}\n"
        f"本地校验发现：{'；'.join(errors)}。\n"
        "请保留原意并修复全部问题，尤其要逐字确认每句五个汉字，"
        "且第一、第二、第四句末字韵母完全相同，第三句韵母不同。只返回一首修复结果。"
    )
