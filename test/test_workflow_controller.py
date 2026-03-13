"""
工作流控制器测试。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOM_ROOT = PROJECT_ROOT / "ecom_reco_agent"
if str(ECOM_ROOT) not in sys.path:
    sys.path.insert(0, str(ECOM_ROOT))

from utils.workflow_controller import (
    build_runtime_guidance,
    dump_workflow_state,
    ensure_retry_allowed_before_category_search,
    request_query_retry,
)


class WorkflowControllerTestCase(unittest.TestCase):
    """验证工作流控制层行为。"""

    def test_confirmation_input_routes_to_stage_7(self) -> None:
        """确认类输入应路由到阶段 7。"""
        guidance = build_runtime_guidance("确认，就按这个方案发吧", max_retry_count=2)
        state = dump_workflow_state()

        self.assertIn("阶段 7：最终确认", guidance)
        self.assertEqual(state["current_stage"], "stage_07_confirmation")

    def test_retry_limit_is_enforced(self) -> None:
        """查询回退次数应受代码上限控制。"""
        build_runtime_guidance("给我推荐春节礼品", max_retry_count=1)
        request_query_retry("第一次回退")
        with self.assertRaises(ValueError):
            request_query_retry("第二次回退")

    def test_retry_gate_blocks_direct_return_to_category_search(self) -> None:
        """进入查询阶段后，未申请回退不允许直接再次做品类标准化。"""
        build_runtime_guidance("推荐春节家电", max_retry_count=2)
        from utils.workflow_controller import record_stage_transition

        record_stage_transition("stage_05_query", reason="test")
        with self.assertRaises(ValueError):
            ensure_retry_allowed_before_category_search()


if __name__ == "__main__":
    unittest.main()
