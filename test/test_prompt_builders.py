"""
Prompt 构建器测试。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ECOM_ROOT = PROJECT_ROOT / "ecom_reco_agent"
if str(ECOM_ROOT) not in sys.path:
    sys.path.insert(0, str(ECOM_ROOT))

from prompts import build_system_instructions
from prompts.builders import PromptContext, build_layered_prompt


class PromptBuilderTestCase(unittest.TestCase):
    """验证 Prompt 分层装配行为。"""

    def test_build_system_instructions_supports_modes(self) -> None:
        """应支持 layered 与 legacy 两种模式。"""
        layered = build_system_instructions("layered")
        legacy = build_system_instructions("legacy")

        self.assertIn("运行时工作流规则", layered)
        self.assertIn("阶段 1：需求解析与规划", legacy)
        self.assertNotEqual(layered, legacy)

    def test_layered_prompt_selects_stage_and_references(self) -> None:
        """应根据上下文选择阶段和 reference 摘要。"""
        bundle = build_layered_prompt(
            PromptContext(
                current_stage="stage_06_integration",
                has_history_result=True,
                needs_data_format_ref=True,
                needs_output_style_ref=True,
                state_summary="已命中历史推荐结果，等待整合新查询结果。",
            )
        )

        self.assertIn("阶段 6：结果整合与输出", bundle.stage_prompt)
        self.assertTrue(any("data-format" in item for item in bundle.references))
        self.assertTrue(any("continuation-rules" in item for item in bundle.references))
        self.assertTrue(any("output-style" in item for item in bundle.references))
        self.assertIn("会话状态摘要", bundle.final_prompt)


if __name__ == "__main__":
    unittest.main()
