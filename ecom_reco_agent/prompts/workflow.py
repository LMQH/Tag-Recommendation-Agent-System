"""
工作流与系统提示词模块。
"""

from .builders.prompt_loader import build_legacy_workflow_text
from .core import CORE_PROMPT

SYSTEM_PROMPT = CORE_PROMPT
WORKFLOW = build_legacy_workflow_text()
COMPLETE_WORKFLOW = f"{SYSTEM_PROMPT}\n\n{WORKFLOW}"

