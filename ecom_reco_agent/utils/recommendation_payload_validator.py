"""
推荐结果入参校验器。
"""

from __future__ import annotations

import ast
import json
from typing import Any, Dict, List, Optional


def _parse_json_like(value: Any) -> Any:
    """解析 JSON 或 Python 字面量字符串。"""
    if not isinstance(value, str):
        return value

    text = value.strip()
    if not text:
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return value


def _validate_festival_scenes(festival_scenes: Any) -> List[Dict[str, Any]]:
    """校验节日场景。"""
    parsed = _parse_json_like(festival_scenes)
    if parsed is None:
        return []
    if not isinstance(parsed, list):
        raise ValueError("festival_scenes 必须是列表或可解析为列表的字符串。")

    required_fields = ("id", "festival_name", "scene_type")
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"festival_scenes 第 {index} 项必须为对象。")
        for field in required_fields:
            value = item.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"festival_scenes 第 {index} 项缺少字段 {field}。")
        normalized.append(item)
    return normalized


def _validate_grouped_recommendations(recommendations: dict[str, Any]) -> None:
    """校验按节日分组的 recommendations。"""
    for festival_name, items in recommendations.items():
        if not isinstance(festival_name, str) or not festival_name.strip():
            raise ValueError("recommendations 的节日分组键不能为空。")
        if not isinstance(items, list):
            raise ValueError(f"recommendations[{festival_name}] 必须是列表。")


def validate_build_review_payload(
    recommendations: Any,
    festival_scenes: Optional[Any] = None,
) -> Dict[str, Any]:
    """校验 build_review_fields 入参。"""
    parsed_recommendations = _parse_json_like(recommendations)
    parsed_festival_scenes = _validate_festival_scenes(festival_scenes)

    if isinstance(parsed_recommendations, dict):
        if "festival_recommendations" in parsed_recommendations:
            return {
                "recommendations": parsed_recommendations,
                "festival_scenes": parsed_festival_scenes,
            }
        _validate_grouped_recommendations(parsed_recommendations)
        if parsed_festival_scenes:
            festival_names = {
                str(item["festival_name"]).strip() for item in parsed_festival_scenes
            }
            unknown_keys = [
                key for key in parsed_recommendations.keys() if key not in festival_names
            ]
            if unknown_keys:
                raise ValueError(
                    "recommendations 存在未在 festival_scenes 中声明的节日分组："
                    + "、".join(unknown_keys)
                )
    elif isinstance(parsed_recommendations, list):
        if len(parsed_festival_scenes) > 1:
            raise ValueError(
                "当 recommendations 为平铺列表时，festival_scenes 不能包含多个节日；"
                "请改为按节日分组的字典。"
            )
    else:
        raise ValueError(
            "recommendations 必须是按节日分组的字典、平铺列表，或可解析为这两类结构的字符串。"
        )

    return {
        "recommendations": parsed_recommendations,
        "festival_scenes": parsed_festival_scenes,
    }


__all__ = ["validate_build_review_payload"]
