"""
运行时工作流控制器。
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, List, Optional

try:
    from agno.utils.log import log_debug
except ImportError:  # pragma: no cover
    def log_debug(*args: Any, **kwargs: Any) -> None:
        """agno 不可用时的空日志函数。"""
        return None

try:
    from prompts.builders import PromptContext, build_layered_prompt
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path

    _parent = Path(__file__).resolve().parents[1]
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from prompts.builders import PromptContext, build_layered_prompt


CONTINUATION_PATTERNS = (
    "加上",
    "加入",
    "还要",
    "添加",
    "另外",
    "以及",
    "删除",
    "不要",
    "只保留",
    "替换",
    "改成",
    "调整",
    "换成",
)

CONFIRMATION_PATTERNS = (
    "确认",
    "可以",
    "好的",
    "没问题",
    "就这样",
    "确定",
    "ok",
    "okay",
    "行",
    "满意",
)

TOOL_STAGE_TRANSITIONS = {
    "get_festival_date_info": "stage_02_festival",
    "get_all_festivals": "stage_02_festival",
    "save_matched_festivals": "stage_03_category",
    "search_category_by_name": "stage_04_planning",
    "query_brand_by_category": "stage_05_query",
    "query_category_by_brand": "stage_05_query",
    "build_review_fields": "stage_06_integration",
    "send_final_recommendation_data": "stage_07_confirmation",
}

_workflow_state_var: ContextVar["WorkflowState"] = ContextVar("workflow_state")


@dataclass
class WorkflowState:
    """运行时工作流状态。"""

    current_stage: str = "stage_01_requirement"
    retry_count: int = 0
    max_retry_count: int = 2
    is_continuation: bool = False
    is_confirmation: bool = False
    has_history_result: bool = False
    needs_data_format_ref: bool = False
    needs_output_style_ref: bool = False
    retry_requested: bool = False
    user_input: str = ""
    stage_history: List[str] = field(default_factory=lambda: ["stage_01_requirement"])
    latest_build_review_fields_result: Optional[str] = None


def _default_state(max_retry_count: int = 2) -> WorkflowState:
    """创建默认状态。"""
    return WorkflowState(max_retry_count=max_retry_count)


def get_workflow_state() -> WorkflowState:
    """获取当前工作流状态。"""
    try:
        return _workflow_state_var.get()
    except LookupError:
        state = _default_state()
        _workflow_state_var.set(state)
        return state


def reset_workflow_state(max_retry_count: int = 2) -> WorkflowState:
    """重置工作流状态。"""
    state = _default_state(max_retry_count=max_retry_count)
    _workflow_state_var.set(state)
    return state


def _contains_pattern(text: str, patterns: tuple[str, ...]) -> bool:
    """检查文本是否包含任一模式。"""
    normalized = text.strip().lower()
    return any(pattern.lower() in normalized for pattern in patterns)


def detect_continuation_intent(user_input: str) -> bool:
    """识别继续对话意图。"""
    return _contains_pattern(user_input, CONTINUATION_PATTERNS)


def detect_confirmation_intent(user_input: str) -> bool:
    """识别确认意图。"""
    normalized = user_input.strip().lower()
    if not normalized:
        return False
    if normalized in {"好", "行"}:
        return True
    return _contains_pattern(user_input, CONFIRMATION_PATTERNS)


def prepare_workflow_state(
    user_input: str,
    max_retry_count: int = 2,
) -> WorkflowState:
    """根据当前用户输入准备工作流状态。"""
    state = reset_workflow_state(max_retry_count=max_retry_count)
    state.user_input = user_input.strip()
    state.is_confirmation = detect_confirmation_intent(user_input)
    state.is_continuation = detect_continuation_intent(user_input)
    state.has_history_result = state.is_continuation or state.is_confirmation
    state.needs_output_style_ref = state.is_confirmation

    if state.is_confirmation:
        state.current_stage = "stage_07_confirmation"
        state.stage_history.append("stage_07_confirmation")
    else:
        state.current_stage = "stage_01_requirement"

    return state


def _append_stage_history(state: WorkflowState, stage_id: str) -> None:
    """追加阶段历史。"""
    if not state.stage_history or state.stage_history[-1] != stage_id:
        state.stage_history.append(stage_id)


def record_stage_transition(stage_id: str, reason: str) -> WorkflowState:
    """记录阶段跳转。"""
    state = get_workflow_state()
    state.current_stage = stage_id
    if stage_id in {"stage_06_integration", "stage_07_confirmation"}:
        state.needs_output_style_ref = True
    if stage_id == "stage_06_integration":
        state.needs_data_format_ref = True
    _append_stage_history(state, stage_id)
    log_debug(f"工作流阶段跳转: {stage_id} | 原因: {reason}", log_level=2)
    return state


def advance_stage_by_tool(tool_name: str) -> WorkflowState:
    """根据工具调用结果推进阶段。"""
    state = get_workflow_state()
    next_stage = TOOL_STAGE_TRANSITIONS.get(tool_name)
    if next_stage is None:
        return state

    if tool_name == "search_category_by_name":
        state.retry_requested = False
    if tool_name == "build_review_fields":
        state.needs_data_format_ref = True
    if tool_name == "send_final_recommendation_data":
        state.is_confirmation = True
    return record_stage_transition(next_stage, reason=f"tool:{tool_name}")


def request_query_retry(reason: str) -> WorkflowState:
    """申请查询回退。"""
    state = get_workflow_state()
    if state.retry_count >= state.max_retry_count:
        raise ValueError(
            f"查询回退次数已达上限 {state.max_retry_count} 次，禁止继续回退。"
        )

    state.retry_count += 1
    state.retry_requested = True
    state.needs_data_format_ref = False
    record_stage_transition("stage_03_category", reason=f"retry:{reason}")
    return state


def ensure_retry_allowed_before_category_search() -> None:
    """在查询阶段回退到品类标准化前进行校验。"""
    state = get_workflow_state()
    if state.current_stage == "stage_05_query" and not state.retry_requested:
        raise ValueError(
            "当前已进入商品库查询阶段，如需回退到品类标准化，必须先调用 request_query_retry。"
        )


def save_latest_build_review_fields_result(result: str) -> None:
    """保存最近一次结构化推荐结果。"""
    state = get_workflow_state()
    state.latest_build_review_fields_result = result
    state.has_history_result = True


def build_state_summary(state: Optional[WorkflowState] = None) -> str:
    """构建状态摘要。"""
    runtime_state = state or get_workflow_state()
    lines = [
        f"- 当前阶段：{runtime_state.current_stage}",
        f"- 是否继续对话：{'是' if runtime_state.is_continuation else '否'}",
        f"- 是否确认场景：{'是' if runtime_state.is_confirmation else '否'}",
        f"- 查询回退次数：{runtime_state.retry_count}/{runtime_state.max_retry_count}",
    ]
    if runtime_state.has_history_result:
        lines.append("- 已检测到需要关注历史推荐结果。")
    if runtime_state.user_input:
        lines.append(f"- 当前用户输入：{runtime_state.user_input}")
    return "\n".join(lines)


def build_runtime_guidance(user_input: str, max_retry_count: int = 2) -> str:
    """构建运行时阶段指导。"""
    state = prepare_workflow_state(user_input=user_input, max_retry_count=max_retry_count)
    prompt_context = PromptContext(
        current_stage=state.current_stage,
        is_continuation=state.is_continuation,
        has_history_result=state.has_history_result,
        needs_data_format_ref=state.needs_data_format_ref,
        needs_output_style_ref=state.needs_output_style_ref,
        retry_count=state.retry_count,
        state_summary=build_state_summary(state),
    )
    bundle = build_layered_prompt(prompt_context)
    return bundle.final_prompt


def dump_workflow_state() -> dict[str, Any]:
    """导出当前状态，供调试查看。"""
    state = get_workflow_state()
    return {
        "current_stage": state.current_stage,
        "retry_count": state.retry_count,
        "max_retry_count": state.max_retry_count,
        "is_continuation": state.is_continuation,
        "is_confirmation": state.is_confirmation,
        "has_history_result": state.has_history_result,
        "needs_data_format_ref": state.needs_data_format_ref,
        "needs_output_style_ref": state.needs_output_style_ref,
        "retry_requested": state.retry_requested,
        "stage_history": list(state.stage_history),
        "user_input": state.user_input,
    }


__all__ = [
    "WorkflowState",
    "advance_stage_by_tool",
    "build_runtime_guidance",
    "build_state_summary",
    "detect_confirmation_intent",
    "detect_continuation_intent",
    "dump_workflow_state",
    "ensure_retry_allowed_before_category_search",
    "get_workflow_state",
    "prepare_workflow_state",
    "record_stage_transition",
    "request_query_retry",
    "reset_workflow_state",
    "save_latest_build_review_fields_result",
]
