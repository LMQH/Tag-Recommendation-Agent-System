"""
提示词模块统一导出。
"""

from __future__ import annotations

from .builders.prompt_loader import build_layered_system_prompt
from .reasoning import REASONING_INSTRUCTIONS
from .workflow import COMPLETE_WORKFLOW, SYSTEM_PROMPT, WORKFLOW

SYSTEM_INSTRUCTIONS_LEGACY = f"{COMPLETE_WORKFLOW}\n\n{REASONING_INSTRUCTIONS}"
SYSTEM_INSTRUCTIONS_LAYERED = (
    f"{build_layered_system_prompt()}\n\n{REASONING_INSTRUCTIONS}"
)
SYSTEM_INSTRUCTIONS = SYSTEM_INSTRUCTIONS_LAYERED


def build_system_instructions(prompt_mode: str = "layered") -> str:
    """根据模式构建系统提示词。"""
    if prompt_mode == "legacy":
        return SYSTEM_INSTRUCTIONS_LEGACY
    return SYSTEM_INSTRUCTIONS_LAYERED


__all__ = [
    "SYSTEM_INSTRUCTIONS",
    "SYSTEM_INSTRUCTIONS_LEGACY",
    "SYSTEM_INSTRUCTIONS_LAYERED",
    "REASONING_INSTRUCTIONS",
    "COMPLETE_WORKFLOW",
    "SYSTEM_PROMPT",
    "WORKFLOW",
    "build_system_instructions",
]
