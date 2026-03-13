"""
推荐数据自定义事件。

用于在runs接口的流式响应中返回推荐数据。

数据格式（以节日为主字段）：
{
    "festival_recommendations": [
        {
            "festival_id": 1,  # 节日 ID（来自数据库）
            "festival_name": "春节",
            "scene_type": "节日营销",
            "brands": [
                {
                    "brandName": "品牌名称",
                    "brandCode": "品牌编码"
                }
            ],
            "categories": [
                {
                    "categoryName": "品类名称",
                    "categoryCode": "品类编码"
                }
            ]
        }
    ]
}
"""

from dataclasses import dataclass, field
from typing import Any, Dict
from agno.run.agent import CustomEvent


@dataclass
class RecommendationDataEvent(CustomEvent):
    """推荐数据自定义事件

    直接接收 build_review_fields 返回的完整数据对象，不做字段提取。
    """
    # 完整的数据对象（包含 recommendations 和 festival_scenes）
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据格式"""
        if not self.data:
            raise ValueError("data 不能为空")

        festival_recommendations = self.data.get("festival_recommendations", [])
        if not festival_recommendations:
            raise ValueError("data 中必须包含 festival_recommendations 字段且不能为空")


__all__ = [
    "RecommendationDataEvent",
]
