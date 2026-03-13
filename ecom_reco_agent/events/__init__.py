"""
事件模块。

包含自定义事件类定义。
"""

try:
    from events.recommendation_event import RecommendationDataEvent
except ImportError:
    # 兼容直接导入
    from .recommendation_event import RecommendationDataEvent

__all__ = [
    "RecommendationDataEvent",
]
