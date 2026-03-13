"""
推荐数据验证与字段生成工具。

功能：
- 验证检索到的品牌+品类数据（必须包含 brandCode 和 categoryCode）
- 去重处理（按 brandCode 和 categoryCode 去重）
- 生成推荐列表数据（用于数据传输和摘要生成）
- 支持按节日分组的数据格式，包含节日 ID
- 将品牌和品类拆分为独立的数组

返回数据格式（以节日为主字段）：
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

import ast
import json
from typing import Any, Dict, List, Optional

from agno.tools import Toolkit
from agno.utils.log import log_debug, log_warning

try:
    from utils.tool_hooks import get_matched_festival_scenes
except ImportError:
    from pathlib import Path
    _parent = Path(__file__).resolve().parents[1]
    import sys
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from utils.tool_hooks import get_matched_festival_scenes

# 当用户指定节日无法匹配（节日为无）时使用的默认节日场景，保证 build_review_fields 可继续执行
DEFAULT_NO_MATCH_FESTIVAL_SCENES: List[Dict[str, Any]] = [
    {"id": "0000", "festival_name": "无匹配节日", "scene_type": "空场景"}
]


class RecommendationReviewToolkit(Toolkit):
    """
    推荐数据验证与字段生成工具。

    工作流程：
    1. 接收原始查询数据
    2. 验证 brandCode 和 categoryCode 是否存在
    3. 去重处理
    4. 生成推荐列表数据
    """

    def __init__(self, **kwargs: Any) -> None:
        tools = [
            self.build_review_fields,
        ]
        super().__init__(
            name="recommendation_review_toolkit",
            tools=tools,
            **kwargs
        )

    def build_review_fields(
        self,
        recommendations: object,
        festival_scenes: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        根据真实推荐数据构造推荐列表数据（用于数据传输和摘要生成）。

        **推荐传入**：按节日分组的字典；平铺 list 在单场景下会自动归入对应节日或「未指定节日」。

        Args:
            recommendations: 按节日分组的字典（优先），或平铺列表（将自动包装）
                - ✅ {"春节": [...], "情人节": [...]}
                - ✅ [{"brandName": "..."}, ...] + festival_scenes 单节日 → 自动包成 {"春节": [...]}
                - ⚠️ 平铺 list 且无 festival_scenes 时归入「未指定节日」，并打 WARNING 日志
            festival_scenes: 节日场景数据列表（必填），与分组键一一对应；每项必须包含：
                - id: 节日 ID（来自数据库，整型或字符串均可）
                - festival_name: 节日名称（与 recommendations 分组键一致）
                - scene_type: 场景类型
                - 格式：[{"id": 1, "festival_name": "春节", "scene_type": "节日营销"}, ...]

        Returns:
            严格 JSON 格式的字符串（双引号），包含 festival_recommendations 数组；
            供 SSE/前端直接 JSON.parse 解析使用。

        Raises:
            ValueError: 若无法解析输入，或多节日场景下仍传平铺 list 且需严格分组时（应改为 dict）

        数据格式示例（brandCode/categoryCode 必须为品牌/品类查询工具返回的真实编码，通常为数字）：
            输入（按节日分组）：
            {
                "春节": [
                    {"brandName": "美的", "brandCode": "1001", ...}
                ],
                "情人节": [
                    {"brandName": "德芙", "brandCode": "1003", ...}
                ]
            }

            festival_scenes:
            [
                {"id": 1, "festival_name": "春节", "scene_type": "节日营销"},
                {"id": 2, "festival_name": "情人节", "scene_type": "节日营销"}
            ]

            输出（本工具直接返回标准 JSON 字符串）：
            {
                "festival_recommendations": [
                    {
                        "festival_id": 1,
                        "festival_name": "春节",
                        "scene_type": "节日营销",
                        "brands": [{"brandName": "美的", "brandCode": "1001"}],
                        "categories": [{"categoryName": "厨房电器", "categoryCode": "2001"}]
                    },
                    {
                        "festival_id": 2,
                        "festival_name": "情人节",
                        "scene_type": "节日营销",
                        "brands": [{"brandName": "德芙", "brandCode": "1003"}],
                        "categories": [{"categoryName": "巧克力", "categoryCode": "2003"}]
                    }
                ]
            }
        """
        # 1) 已是最终结构则序列化为 JSON 字符串后返回
        if isinstance(recommendations, dict) and "festival_recommendations" in recommendations:
            return json.dumps(recommendations, ensure_ascii=False, default=str)

        # 2) festival_scenes：显式传入优先；未传或为空时从会话变量读取（阶段 2 调用 save_matched_festivals 写入的）
        if not festival_scenes or (isinstance(festival_scenes, list) and len(festival_scenes) == 0):
            stored = get_matched_festival_scenes()
            if stored and len(stored) > 0:
                festival_scenes = stored
        # 无匹配节日时使用默认场景（id=0000、无匹配节日、空场景），使后续步骤可正常执行
        if not festival_scenes or (isinstance(festival_scenes, list) and len(festival_scenes) == 0):
            festival_scenes = list(DEFAULT_NO_MATCH_FESTIVAL_SCENES)
            log_warning(
                "未传入 festival_scenes 且会话中无匹配节日，已使用默认「无匹配节日」场景（id=0000），以便流程继续。"
            )
        if not festival_scenes or not isinstance(festival_scenes, list):
            raise ValueError(
                "必须传入 festival_scenes（非空列表），或先在第二阶段调用 save_matched_festivals 保存筛选后的节日；"
                "每项须含 id、festival_name、scene_type，所有真实节日均有 ID，不可省略。"
            )

        # 3) 解析为「按节日分组的 dict」或「平铺 list」并包装（无 festival_scenes 时 _wrap 会报错）
        grouped = self._coerce_to_festival_grouped(recommendations, festival_scenes)

        festival_names = [k for k in grouped.keys() if isinstance(k, str)]
        if not festival_names:
            raise ValueError("recommendations 解析后分组为空，请检查输入。")
        if "未指定节日" in grouped:
            raise ValueError(
                "存在「未指定节日」分组：平铺列表时必须传入 festival_scenes 且能对应到具体节日；"
                "请改为按 {\"节日名\": [...]} 传入，或传入含 id 的 festival_scenes。"
            )
        if not self._is_festival_grouped_dict(grouped):
            raise ValueError(
                "recommendations 分组格式无效：期望每个节日键对应一个列表。"
                f"当前键：{list(grouped.keys())}"
            )
        suspicious = [k for k in festival_names if not str(k).strip()]
        if suspicious:
            raise ValueError(f"recommendations 分组键不能为空。当前键：{list(grouped.keys())}")

        data = self._transform_festival_grouped_data(grouped, festival_scenes)
        return json.dumps(data, ensure_ascii=False, default=str)

    def _coerce_to_festival_grouped(
        self,
        recommendations: object,
        festival_scenes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, List[Any]]:
        """
        将 list / dict / JSON 字符串等统一转为按节日分组的 dict。

        - 已是 {"春节": [...], ...} 且值为 list：直接返回。
        - 平铺 list：须配合 festival_scenes（单节日包一层；多节日合并到首个并 WARNING）。
        - rec_* 风格 dict：先压成 list 再包装。
        - 无 festival_scenes 且为平铺 list 时直接报错（不再使用「未指定节日」）。
        """
        # 字符串先解析成 Python 对象
        if isinstance(recommendations, str):
            recommendations = self._parse_string_to_object(recommendations)

        if isinstance(recommendations, dict):
            if "festival_recommendations" in recommendations:
                # 调用方应在 build_review_fields 开头已 return；双重保险
                raise ValueError("不应将 festival_recommendations 顶层结构传入 _coerce_to_festival_grouped")
            if self._is_festival_grouped_dict(recommendations):
                return dict(recommendations)
            # 否则视为 rec_* 等扁平 dict，转成 list 再走 list 分支
            flat_list = self._dict_recommendations_to_list(recommendations)
            return self._wrap_flat_list_as_grouped(flat_list, festival_scenes)

        if isinstance(recommendations, list):
            return self._wrap_flat_list_as_grouped(recommendations, festival_scenes)

        raise ValueError(
            "recommendations 类型不支持，请传入 list、按节日分组的 dict 或 JSON 字符串。"
            f"当前类型：{type(recommendations).__name__}"
        )

    def _parse_string_to_object(self, s: str) -> object:
        """将 JSON / Python 字面量 / 截取片段解析为 list 或 dict。"""
        s = s.strip()
        try:
            parsed = json.loads(s)
            if isinstance(parsed, (list, dict)):
                return parsed
        except json.JSONDecodeError:
            pass
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, (list, dict)):
                return parsed
        except (ValueError, SyntaxError):
            pass
        start = s.find("[")
        end = s.rfind("]")
        if start != -1 and end != -1 and end > start:
            snippet = s[start : end + 1]
            try:
                parsed = json.loads(snippet)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(snippet)
                    if isinstance(parsed, list):
                        return parsed
                except (ValueError, SyntaxError):
                    pass
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = s[start : end + 1]
            try:
                parsed = json.loads(snippet)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(snippet)
                    if isinstance(parsed, dict):
                        return parsed
                except (ValueError, SyntaxError):
                    pass
        raise ValueError("无法将 recommendations 字符串解析为 list 或 dict")

    def _is_festival_grouped_dict(self, data: Dict[str, Any]) -> bool:
        """判断是否为「节日名 -> list」分组结构（值须为 list，避免与 rec_* 字典混淆）。"""
        if not data:
            return False
        for k, v in data.items():
            if not isinstance(k, str):
                return False
            if not isinstance(v, list):
                return False
        return True

    def _wrap_flat_list_as_grouped(
        self,
        flat_list: List[Any],
        festival_scenes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, List[Any]]:
        """将平铺 list 包成单键分组 dict；必须能用 festival_scenes 落到具体节日（均有 id）。"""
        if not isinstance(flat_list, list):
            flat_list = list(flat_list) if flat_list else []

        if not festival_scenes:
            if flat_list:
                raise ValueError(
                    "平铺列表必须同时传入 festival_scenes（含 id、festival_name、scene_type），"
                    "否则无法写入 festival_id；请按 {\"春节\": [...]} 分组传入。"
                )
            return {}

        names = [
            fs.get("festival_name", "").strip()
            for fs in festival_scenes
            if isinstance(fs, dict) and fs.get("festival_name")
        ]
        if not names:
            raise ValueError(
                "festival_scenes 中缺少有效的 festival_name，无法为平铺列表归类；"
                "请传入 get_all_festivals 筛选后的完整项（含 id）。"
            )
        if len(names) == 1:
            return {names[0]: flat_list}
        log_warning(
            "build_review_fields 收到平铺列表且 festival_scenes 含多个节日，"
            "已合并到首个节日下；建议改为按节日分组 dict 传入。"
        )
        return {names[0]: flat_list}

    def _normalize_recommendations(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将原始推荐数据规范化为最小字段并去重

        Args:
            raw_data: 原始推荐数据列表

        Returns:
            规范化后的推荐数据列表
        """
        valid_recommendations: List[Dict[str, Any]] = []
        seen_combinations = set()

        for item in raw_data:
            if not isinstance(item, dict):
                log_debug(f"跳过非字典类型的数据: {type(item).__name__}", log_level=1)
                continue

            # 支持多种字段名格式
            brand_code = (
                item.get("brandCode") or
                item.get("brand_code") or
                item.get("brand")
            )
            category_code = (
                item.get("categoryCode") or
                item.get("category_code") or
                item.get("category")
            )

            # 过滤掉无效值：None、空字符串、"N/A"（不区分大小写）
            if category_code:
                category_code_str = str(category_code).strip().upper()
                if category_code_str in ("N/A", "NA", "NULL", "NONE", ""):
                    category_code = None

            if brand_code:
                brand_code_str = str(brand_code).strip().upper()
                if brand_code_str in ("N/A", "NA", "NULL", "NONE", ""):
                    brand_code = None

            if not brand_code or not category_code:
                log_debug(f"跳过缺少必填字段的数据: brandCode={brand_code}, categoryCode={category_code}, 现有字段: {list(item.keys())}", log_level=1)
                continue

            combination_key = f"{brand_code}_{category_code}"
            if combination_key in seen_combinations:
                log_debug(f"跳过重复组合: {combination_key}", log_level=1)
                continue
            seen_combinations.add(combination_key)

            # 构建规范化数据
            normalized_item = {
                "brandName": item.get("brandName") or item.get("brand_name") or "未知品牌",
                "brandCode": str(brand_code),
                "categoryName": item.get("categoryName") or item.get("category_name") or "未知品类",
                "categoryCode": str(category_code),
            }

            valid_recommendations.append(normalized_item)

        return valid_recommendations

    def _parse_recommendations(self, recommendations: object) -> List[Dict[str, Any]]:
        """解析推荐数据，兼容 list / dict / JSON 字符串 / Python 字面量字符串。"""
        if isinstance(recommendations, list):
            return recommendations

        if isinstance(recommendations, dict):
            return self._dict_recommendations_to_list(recommendations)

        if isinstance(recommendations, str):
            try:
                parsed = json.loads(recommendations)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    return self._dict_recommendations_to_list(parsed)
                return []
            except json.JSONDecodeError:
                pass

            try:
                parsed = ast.literal_eval(recommendations)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    return self._dict_recommendations_to_list(parsed)
                return []
            except (ValueError, SyntaxError):
                pass

            start = recommendations.find("[")
            end = recommendations.rfind("]")
            if start != -1 and end != -1 and end > start:
                snippet = recommendations[start:end + 1]
                try:
                    parsed = json.loads(snippet)
                    if isinstance(parsed, list):
                        return parsed
                    if isinstance(parsed, dict):
                        return self._dict_recommendations_to_list(parsed)
                    return []
                except json.JSONDecodeError:
                    try:
                        parsed = ast.literal_eval(snippet)
                        if isinstance(parsed, list):
                            return parsed
                        if isinstance(parsed, dict):
                            return self._dict_recommendations_to_list(parsed)
                        return []
                    except (ValueError, SyntaxError):
                        return []

        return []

    def _dict_recommendations_to_list(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将 {'rec_1': {...}, 'rec_2': {...}} 转为按序 list。

        过滤掉非字典类型的值，确保返回的列表中每个元素都是字典。
        """
        def _key_order(k: str) -> int:
            if isinstance(k, str) and "_" in k:
                suffix = k.rsplit("_", 1)[-1]
                if suffix.isdigit():
                    return int(suffix)
            return 10**9

        keys = list(data.keys())
        if all(isinstance(k, str) and k.startswith(("rec_", "reject_")) for k in keys):
            keys = sorted(keys, key=_key_order)

        # 只保留字典类型的值
        result = []
        for k in keys:
            value = data[k]
            if isinstance(value, dict):
                result.append(value)
            else:
                log_debug(f"_dict_recommendations_to_list: 跳过非字典类型的值 (key={k}, type={type(value).__name__})", log_level=1)

        return result

    def _is_festival_name(self, key: str) -> bool:
        """判断是否是节日名称（简单的启发式判断）

        Args:
            key: 待判断的字符串

        Returns:
            是否是节日名称
        """
        # 常见的节日关键词
        festival_keywords = [
            "春节", "情人节", "清明节", "劳动节", "端午节",
            "中秋节", "国庆节", "元旦", "圣诞", "七夕", "元宵",
            "妇女节", "儿童节", "教师节", "重阳节",
            "除夕", "腊八", "小年", "年货", "清明", "端午", "中秋",
        ]
        return any(keyword in key for keyword in festival_keywords)

    def _transform_festival_grouped_data(
        self,
        grouped_data: Dict[str, Any],
        festival_scenes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        转换按节日分组的数据为 festival_recommendations 格式，将品牌和品类拆分为独立数组。

        业务逻辑：
        - 每个节日的输入是独立的，可能包含该节日适合的所有商品
        - 将 recommendations 拆分为 brands 和 categories 两个独立数组
        - brands 按 brandCode 去重，categories 按 categoryCode 去重
        - 从 festival_scenes 中提取节日 ID，包含在最终输出中

        Args:
            grouped_data: 按节日分组的数据，例如 {"春节": [...], "情人节": [...]}
            festival_scenes: 节日场景数据列表，必须包含 id、festival_name、scene_type 三个字段

        Returns:
            festival_recommendations 格式的数据，包含 festival_id、brands、categories 字段
        """
        # 第一步：为每个节日收集 brands 和 categories（按 code 去重）
        festival_brands_map: Dict[str, Dict[str, Dict[str, str]]] = {}  # {festival_name: {brandCode: brandData}}
        festival_categories_map: Dict[str, Dict[str, Dict[str, str]]] = {}  # {festival_name: {categoryCode: categoryData}}

        for festival_name, recommendations in grouped_data.items():
            if not isinstance(recommendations, list):
                continue

            # 初始化该节日的 brands 和 categories 集合
            if festival_name not in festival_brands_map:
                festival_brands_map[festival_name] = {}
            if festival_name not in festival_categories_map:
                festival_categories_map[festival_name] = {}

            for rec in recommendations:
                if not isinstance(rec, dict):
                    continue

                brand_code = rec.get("brandCode", "")
                category_code = rec.get("categoryCode", "")

                # 收集品牌（按 brandCode 去重）
                if brand_code and brand_code not in festival_brands_map[festival_name]:
                    festival_brands_map[festival_name][brand_code] = {
                        "brandName": rec.get("brandName", "未知品牌"),
                        "brandCode": brand_code
                    }

                # 收集品类（按 categoryCode 去重）
                if category_code and category_code not in festival_categories_map[festival_name]:
                    festival_categories_map[festival_name][category_code] = {
                        "categoryName": rec.get("categoryName", "未知品类"),
                        "categoryCode": category_code
                    }

        # 第二步：构建 festival_name 到 scene_type 和 id 的映射
        festival_scene_map: Dict[str, str] = {}
        festival_id_map: Dict[str, Any] = {}

        for fs in festival_scenes:
            if not isinstance(fs, dict):
                continue
            festival_name = (fs.get("festival_name") or "").strip()
            if not festival_name:
                continue
            festival_id = fs.get("id")
            if festival_id is None or festival_id == "":
                raise ValueError(
                    f"festival_scenes 中节日「{festival_name}」缺少 id；真实节日均有 ID，请传入数据库返回的 id。"
                )
            festival_id_map[festival_name] = festival_id
            festival_scene_map[festival_name] = fs.get("scene_type") or "节日营销"

        # 第三步：构建 festival_recommendations 结构
        festival_rec_list = []

        for festival_name in grouped_data.keys():
            # 每个节日必须有 festival_id
            if festival_name not in festival_id_map:
                raise ValueError(
                    f"分组键「{festival_name}」在 festival_scenes 中无对应项或缺少 id；"
                    f"请保证 recommendations 的键与 festival_scenes[].festival_name 一致且均含 id。"
                    f"当前已注册节日：{list(festival_id_map.keys())}"
                )

            # 获取该节日的 brands 和 categories（转换为列表）
            brands_list = list(festival_brands_map.get(festival_name, {}).values())
            categories_list = list(festival_categories_map.get(festival_name, {}).values())

            scene_type = festival_scene_map.get(festival_name, "节日营销")

            # 构建节日推荐对象，顺序固定为 id → name → scene_type → brands → categories
            festival_rec_list.append({
                "festival_id": festival_id_map[festival_name],
                "festival_name": festival_name,
                "scene_type": scene_type,
                "brands": brands_list,
                "categories": categories_list,
            })

        return {
            "festival_recommendations": festival_rec_list
        }


def create_recommendation_review_toolkit(**kwargs: Any) -> RecommendationReviewToolkit:
    """
    工厂函数，便于在 Agent 中创建并注册工具。
    """
    return RecommendationReviewToolkit(**kwargs)


__all__ = [
    "RecommendationReviewToolkit",
    "create_recommendation_review_toolkit",
]
