"""
Prompt 注册表。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ReferenceDefinition:
    """Reference 定义。"""

    name: str
    file_name: str
    summary_points: List[str]


@dataclass(frozen=True)
class StageDefinition:
    """阶段 Prompt 定义。"""

    stage_id: str
    title: str
    file_name: str
    default_references: List[str] = field(default_factory=list)


@dataclass
class PromptContext:
    """运行时 Prompt 上下文。"""

    current_stage: str = "stage_01_requirement"
    is_continuation: bool = False
    has_history_result: bool = False
    needs_data_format_ref: bool = False
    needs_output_style_ref: bool = False
    retry_count: int = 0
    state_summary: str = ""


@dataclass
class PromptBundle:
    """装配后的 Prompt 内容。"""

    core_prompt: str
    stage_prompt: str
    references: List[str]
    final_prompt: str


STAGE_DEFINITIONS: Dict[str, StageDefinition] = {
    "stage_01_requirement": StageDefinition(
        stage_id="stage_01_requirement",
        title="需求解析与规划",
        file_name="stage_01_requirement.md",
        default_references=["continuation-rules"],
    ),
    "stage_02_festival": StageDefinition(
        stage_id="stage_02_festival",
        title="节日匹配",
        file_name="stage_02_festival.md",
        default_references=["festival-matching"],
    ),
    "stage_03_category": StageDefinition(
        stage_id="stage_03_category",
        title="品类标准化",
        file_name="stage_03_category.md",
        default_references=["category-normalization"],
    ),
    "stage_04_planning": StageDefinition(
        stage_id="stage_04_planning",
        title="查询规划",
        file_name="stage_04_planning.md",
    ),
    "stage_05_query": StageDefinition(
        stage_id="stage_05_query",
        title="商品库查询",
        file_name="stage_05_query.md",
        default_references=["category-normalization"],
    ),
    "stage_06_integration": StageDefinition(
        stage_id="stage_06_integration",
        title="结果整合与输出",
        file_name="stage_06_integration.md",
        default_references=["data-format", "continuation-rules", "output-style"],
    ),
    "stage_07_confirmation": StageDefinition(
        stage_id="stage_07_confirmation",
        title="最终确认",
        file_name="stage_07_confirmation.md",
        default_references=["output-style"],
    ),
}

REFERENCE_DEFINITIONS: Dict[str, ReferenceDefinition] = {
    "data-format": ReferenceDefinition(
        name="data-format",
        file_name="data-format.md",
        summary_points=[
            "`build_review_fields` 输入必须按节日分组。",
            "`festival_scenes` 每项必须包含 `id`、`festival_name`、`scene_type`。",
            "品牌按 `brandCode` 去重，品类按 `categoryCode` 去重。",
            "禁止传入自造编码或平铺列表。",
        ],
    ),
    "festival-matching": ReferenceDefinition(
        name="festival-matching",
        file_name="festival-matching.md",
        summary_points=[
            "只保留与用户意图匹配的节日记录。",
            "库中无匹配时必须调用 `save_matched_festivals([])`。",
            "`festival_scenes` 只能来自真实节日工具结果。",
        ],
    ),
    "category-normalization": ReferenceDefinition(
        name="category-normalization",
        file_name="category-normalization.md",
        summary_points=[
            "优先使用用户明确给出的品类词。",
            "标准化依赖 `search_category_by_name`。",
            "优先选择 `category_level=3`，结果不足时再细化。",
        ],
    ),
    "continuation-rules": ReferenceDefinition(
        name="continuation-rules",
        file_name="continuation-rules.md",
        summary_points=[
            "识别继续对话信号词并检查最近一次结构化推荐结果。",
            "只有字段真实且可追溯时才能整合历史数据。",
            "缺少可靠编码时不要强行合并旧结果。",
        ],
    ),
    "output-style": ReferenceDefinition(
        name="output-style",
        file_name="output-style.md",
        summary_points=[
            "仅阶段 6、7 可以生成面向用户的摘要。",
            "使用中文、简洁 Markdown 和友好语气。",
            "不要输出内部推理链路。",
        ],
    ),
}
