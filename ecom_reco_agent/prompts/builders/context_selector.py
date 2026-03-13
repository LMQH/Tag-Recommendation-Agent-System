"""
Prompt 上下文选择器。
"""

from __future__ import annotations

from typing import List

from .prompt_registry import PromptContext, REFERENCE_DEFINITIONS, STAGE_DEFINITIONS


def select_stage_id(context: PromptContext) -> str:
    """选择当前阶段。"""
    if context.current_stage in STAGE_DEFINITIONS:
        return context.current_stage
    return "stage_01_requirement"


def select_reference_names(context: PromptContext) -> List[str]:
    """根据上下文选择 reference。"""
    stage_id = select_stage_id(context)
    stage_definition = STAGE_DEFINITIONS[stage_id]
    selected = list(stage_definition.default_references)

    if context.has_history_result and "continuation-rules" not in selected:
        selected.append("continuation-rules")
    if context.needs_data_format_ref and "data-format" not in selected:
        selected.append("data-format")
    if context.needs_output_style_ref and "output-style" not in selected:
        selected.append("output-style")

    return [name for name in selected if name in REFERENCE_DEFINITIONS]
