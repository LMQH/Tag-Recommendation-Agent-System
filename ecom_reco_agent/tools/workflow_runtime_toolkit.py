"""
运行时工作流工具。
"""

from __future__ import annotations

import json
from typing import Any

from agno.tools import Toolkit, tool

try:
    from utils.workflow_controller import (
        build_runtime_guidance,
        dump_workflow_state,
        request_query_retry,
    )
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path

    _parent = Path(__file__).resolve().parents[1]
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from utils.workflow_controller import (
        build_runtime_guidance,
        dump_workflow_state,
        request_query_retry,
    )


class WorkflowRuntimeToolkit(Toolkit):
    """运行时工作流工具。"""

    def __init__(self, max_retry_count: int = 2, **kwargs: Any) -> None:
        self.max_retry_count = max_retry_count
        tools = [
            self.get_workflow_guidance,
            self.request_query_retry,
            self.get_workflow_state_snapshot,
        ]
        super().__init__(
            name="workflow_runtime_toolkit",
            tools=tools,
            **kwargs,
        )

    @tool()
    def get_workflow_guidance(self, user_input: str) -> str:
        """根据当前用户输入返回本轮运行时阶段指导。"""
        return build_runtime_guidance(
            user_input=user_input,
            max_retry_count=self.max_retry_count,
        )

    @tool()
    def request_query_retry(self, reason: str) -> str:
        """在查询结果不足时申请回退到品类标准化阶段。"""
        state = request_query_retry(reason=reason)
        return (
            f"已批准第 {state.retry_count} 次查询回退，请返回阶段 3 重新做品类标准化。"
        )

    @tool()
    def get_workflow_state_snapshot(self) -> str:
        """返回当前工作流状态快照，便于调试。"""
        return json.dumps(dump_workflow_state(), ensure_ascii=False, default=str)


def create_workflow_runtime_toolkit(
    max_retry_count: int = 2,
    **kwargs: Any,
) -> WorkflowRuntimeToolkit:
    """创建运行时工作流工具。"""
    return WorkflowRuntimeToolkit(max_retry_count=max_retry_count, **kwargs)


__all__ = [
    "WorkflowRuntimeToolkit",
    "create_workflow_runtime_toolkit",
]
