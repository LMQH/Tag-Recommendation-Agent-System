"""
最终推荐数据发送工具。

功能：
- 在用户确认后，发送最终的推荐数据
- 接收 build_review_fields 返回的完整数据
- 通过自定义事件在runs接口的流式响应中返回推荐数据

数据格式示例（以节日为主字段）：
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

from __future__ import annotations

import json
from typing import Any

from agno.tools import Toolkit, tool
from agno.utils.log import log_info, log_error

try:
    from events.recommendation_event import RecommendationDataEvent
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from events.recommendation_event import RecommendationDataEvent


class FinalRecommendationSenderToolkit(Toolkit):
    """
    最终推荐数据发送工具。

    工作流程：
    1. 在用户确认后接收 build_review_fields 返回的完整数据
    2. 通过自定义事件在runs接口的流式响应中返回推荐数据
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        初始化最终推荐数据发送工具。

        数据通过自定义事件返回，保留 build_review_fields 的原始格式。
        """
        tools = [
            self.send_final_recommendation_data,
        ]
        super().__init__(
            name="final_recommendation_sender_toolkit",
            tools=tools,
            **kwargs
        )

    @tool()
    def send_final_recommendation_data(
        self,
        recommendations_data: object,
    ):
        """
        发送最终推荐数据到前端（仅在用户确认后调用）。

        Args:
            recommendations_data: build_review_fields 返回的完整数据（dict 或 JSON 字符串）
                包含 festival_recommendations 字段，每个节日包含 festival_id、brands、categories

        数据格式示例：
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

        Yields:
            RecommendationDataEvent: 推荐数据自定义事件（通过 yield 发送到 SSE 流）

        Returns:
            str: 工具结果文本（返回给模型用于生成聊天内容）
        """
        try:
            # 解析输入数据
            if isinstance(recommendations_data, str):
                try:
                    data = json.loads(recommendations_data)
                except json.JSONDecodeError:
                    log_error(f"无法解析 JSON 字符串: {recommendations_data[:100]}...")
                    return "标签数据传输失败：无法解析推荐数据"
            elif isinstance(recommendations_data, dict):
                data = recommendations_data
            else:
                log_error(f"不支持的输入类型: {type(recommendations_data)}")
                return f"标签数据传输失败：不支持的输入类型 {type(recommendations_data).__name__}"

            # 直接传递完整数据对象，不做字段提取
            yield RecommendationDataEvent(data=data)

            # 记录用户确认日志（INFO级别，不包含具体标签数据）
            festival_recommendations = data.get("festival_recommendations", [])
            festival_count = len(festival_recommendations)

            # 计算所有节日的品牌和品类总数
            total_brands = 0
            total_categories = 0
            for festival in festival_recommendations:
                brands = festival.get("brands", [])
                categories = festival.get("categories", [])
                total_brands += len(brands)
                total_categories += len(categories)

            log_info(f"用户已确认推荐方案 | 节日数量: {festival_count} 个 | 品牌总数: {total_brands} 个 | 品类总数: {total_categories} 个")

            # 返回工具结果文本（返回给模型，用于生成聊天内容）
            return f"标签数据已传输成功，共 {festival_count} 个节日场景，包含 {total_brands} 个品牌和 {total_categories} 个品类"

        except Exception as e:
            log_error(f"传输推荐数据时发生错误: {e}")
            return f"标签数据传输失败：{str(e)}"


def create_final_recommendation_sender_toolkit(**kwargs: Any) -> FinalRecommendationSenderToolkit:
    """
    工厂函数，便于在 Agent 中创建并注册工具。
    """
    return FinalRecommendationSenderToolkit(**kwargs)


__all__ = [
    "FinalRecommendationSenderToolkit",
    "create_final_recommendation_sender_toolkit",
]
