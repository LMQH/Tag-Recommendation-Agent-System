"""
Prompt 读取与装配。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, List

from ..core import CORE_PROMPT
from .context_selector import select_reference_names, select_stage_id
from .prompt_registry import (
    PromptBundle,
    PromptContext,
    REFERENCE_DEFINITIONS,
    STAGE_DEFINITIONS,
)

PROMPTS_DIR = Path(__file__).resolve().parents[1]
STAGES_DIR = PROMPTS_DIR / "stages"
REFERENCES_DIR = PROMPTS_DIR / "references"


@lru_cache(maxsize=64)
def _read_text(file_path: str) -> str:
    """读取并缓存文本文件。"""
    return Path(file_path).read_text(encoding="utf-8").strip()


def load_stage_prompt(stage_id: str) -> str:
    """加载指定阶段 Prompt。"""
    stage_definition = STAGE_DEFINITIONS[stage_id]
    return _read_text(str(STAGES_DIR / stage_definition.file_name))


def load_reference_text(reference_name: str) -> str:
    """加载 reference 全文。"""
    reference_definition = REFERENCE_DEFINITIONS[reference_name]
    return _read_text(str(REFERENCES_DIR / reference_definition.file_name))


def build_reference_summary(reference_names: Iterable[str]) -> List[str]:
    """生成 reference 摘要块。"""
    summaries: List[str] = []
    for reference_name in reference_names:
        definition = REFERENCE_DEFINITIONS[reference_name]
        summary = "\n".join(f"- {point}" for point in definition.summary_points)
        summaries.append(f"## Reference 摘要：{reference_name}\n{summary}")
    return summaries


def build_layered_prompt(context: PromptContext | None = None) -> PromptBundle:
    """构建 layered 模式 Prompt。"""
    runtime_context = context or PromptContext()
    stage_id = select_stage_id(runtime_context)
    reference_names = select_reference_names(runtime_context)
    stage_prompt = load_stage_prompt(stage_id)
    references = build_reference_summary(reference_names)

    parts = [CORE_PROMPT, stage_prompt, *references]
    if runtime_context.state_summary:
        parts.append(f"## 会话状态摘要\n{runtime_context.state_summary}")
    final_prompt = "\n\n".join(part for part in parts if part)
    return PromptBundle(
        core_prompt=CORE_PROMPT,
        stage_prompt=stage_prompt,
        references=references,
        final_prompt=final_prompt,
    )


def build_stage_overview() -> str:
    """构建全部阶段的精简概览。"""
    sections = [load_stage_prompt(stage_id) for stage_id in STAGE_DEFINITIONS]
    return "\n\n".join(sections)


def build_legacy_workflow_text() -> str:
    """构建兼容旧接口的静态 workflow 文本。"""
    return build_stage_overview()


def build_layered_system_prompt() -> str:
    """构建默认 layered 系统 Prompt。"""
    runtime_rules = """## 运行时工作流规则
- 每轮收到用户输入后，先调用 `get_workflow_guidance(user_input=用户原话)` 获取当前阶段指导。
- 只执行运行时指导中允许的工具，不要跨阶段混用工具。
- 当商品库查询结果不足、需要回退到品类标准化时，必须先调用 `request_query_retry(reason=原因)`，获批后才能继续。
- `build_review_fields` 与 `send_final_recommendation_data` 的数据格式以工具自身实现为准，不要在工具外自行改造结构。
- 只有用户明确确认后，才能调用 `send_final_recommendation_data`。
"""
    parts = [CORE_PROMPT, runtime_rules]
    return "\n\n".join(parts)
