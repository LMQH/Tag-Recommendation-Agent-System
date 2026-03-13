"""
AI 装修【真实商品库】品牌/分类关联查询接口的 Agno 工具封装。

【重要】这是真实商品库查询工具：
- 只有查询到的品牌+品类组合才有对应商品可供推荐
- 查询不到编码（返回空列表）意味着商品库中没有该商品，用户无法购买
- 禁止自行编造或补全未查询到的品牌/品类编码

提供两个工具：
- query_category_by_brand：传品牌编码/名称，查关联分类列表
- query_brand_by_category：传分类编码/名称，查关联品牌列表
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests  # type: ignore
from agno.tools import Toolkit
from agno.utils.log import log_info, log_debug, log_warning, log_error


class BrandCategoryApiToolkit(Toolkit):
    """
    【真实商品库】品牌/分类关联查询工具。

    重要：这是真实商品库的查询接口，用于查询实际有货可售的品牌+品类组合。
    - 查询结果代表商品库中真实存在的商品
    - 返回空列表表示没有对应商品，禁止推荐
    - 禁止自行编造或补全未查询到的品牌/品类编码

    提供两个查询接口：
    - /open/api/aiTrim/queryCategoryByBrand：品牌查分类
    - /open/api/aiTrim/queryBrandByCategory：分类查品牌
    """

    def __init__(
        self,
        base_url: str = "https://api-show.haoxiny.com/open/api/aiTrim",
        timeout: float = 8.0,
        session: Optional[requests.Session] = None,
        max_results: int = 50,
        **kwargs: Any,
    ) -> None:
        """
        Args:
            base_url: 服务基础地址，结尾无需带 /open/api/aiTrim
            timeout: HTTP 请求超时时间（秒）
            session: 可注入自定义 requests.Session，便于复用连接/代理
            max_results: 最大返回结果数量，默认50，超过此数量将被截断
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.max_results = max_results
        # 用于避免重复查询品牌编码的简单缓存：key=(categoryCode, brandName)
        self._brand_code_cache: dict[tuple[str, str], Optional[str]] = {}

        tools = [
            self.query_category_by_brand,
            self.query_brand_by_category,
        ]
        super().__init__(name="brand_category_api_toolkit", tools=tools, **kwargs)

    # ----------------------------- public tools ----------------------------- #
    def query_category_by_brand(
        self,
        brand_code: Optional[str] = None,
        brand_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        【真实商品库查询】根据品牌编码或品牌名称查询该品牌在商品库中有货的分类列表。

        重要说明：
        - 这是真实商品库查询，返回的是实际有货可售的品牌+品类组合
        - 返回空列表表示商品库中没有该品牌的商品，不可推荐
        - 只有返回结果中的组合才能推荐给用户

        Args:
            brand_code: 品牌编码（精准匹配）
            brand_name: 品牌名称（支持模糊匹配）

        Returns:
            商品库中该品牌有货的分类列表，每项包含：
            - brandCode/brandName：品牌编码和名称
            - categoryCode/categoryName：分类编码和名称
            返回空列表 [] 表示商品库中没有该品牌的商品。
            注意：返回结果最多包含 max_results 条（默认50条），超过部分会被截断。
        """
        if not (brand_code or brand_name):
            raise ValueError("brand_code 和 brand_name 不能同时为空")

        payload = {
            "brandCode": brand_code,
            "brandName": brand_name,
            # 接口共享 DTO，其余字段传 None 不参与查询
            "categoryCode": None,
            "categoryName": None,
        }
        log_debug(f"查询品牌关联分类 | 品牌编码: {brand_code} | 品牌名称: {brand_name}", log_level=2)
        raw = self._post("/queryCategoryByBrand", payload)
        normalized: List[Dict[str, Any]] = []
        for item in raw:
            cat_code = (item or {}).get("categoryCode")
            cat_name = (item or {}).get("categoryName")
            b_code = (item or {}).get("brandCode") or brand_code
            b_name = (item or {}).get("brandName") or brand_name

            # 若品牌编码缺失且有品牌名+分类编码，尝试二次查询品牌编码
            if not b_code and b_name and cat_code:
                b_code = self._lookup_brand_code_by_category(cat_code, b_name) or b_code

            normalized.append(
                {
                    "brandCode": b_code,
                    "brandName": b_name,
                    "categoryCode": cat_code,
                    "categoryName": cat_name,
                }
            )
        
        # 限制返回数量，避免一次性返回过多内容
        if len(normalized) > self.max_results:
            log_debug(
                f"查询结果数量 {len(normalized)} 超过最大限制 {self.max_results}，已截断为前 {self.max_results} 条",
                log_level=2
            )
            normalized = normalized[: self.max_results]
        
        log_debug(f"查询品牌关联分类完成 | 品牌: {brand_name or brand_code} | 返回 {len(normalized)} 个分类", log_level=1)
        log_debug(f"数据查询成功 | 品牌: {brand_name or brand_code} | 返回 {len(normalized)} 个分类", log_level=1)
        return normalized

    def query_brand_by_category(
        self,
        category_code: Optional[str] = None,
        category_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        【真实商品库查询】根据分类编码或分类名称查询该分类在商品库中有货的品牌列表。

        重要说明：
        - 这是真实商品库查询，返回的是实际有货可售的品牌+品类组合
        - 返回空列表表示商品库中没有该分类的商品，不可推荐
        - 只有返回结果中的组合才能推荐给用户

        Args:
            category_code: 分类编码（精准匹配）
            category_name: 分类名称（支持模糊匹配）

        Returns:
            商品库中该分类有货的品牌列表，每项包含：
            - categoryCode/categoryName：分类编码和名称
            - brandCode/brandName：品牌编码和名称
            返回空列表 [] 表示商品库中没有该分类的商品。
            注意：返回结果最多包含 max_results 条（默认50条），超过部分会被截断。
        """
        if not (category_code or category_name):
            raise ValueError("category_code 和 category_name 不能同时为空")

        payload = {
            "categoryCode": category_code,
            "categoryName": category_name,
            "brandCode": None,
            "brandName": None,
        }
        log_debug(f"查询分类关联品牌 | 分类编码: {category_code} | 分类名称: {category_name}", log_level=2)
        raw = self._post("/queryBrandByCategory", payload)
        normalized = []
        for item in raw:
            # 获取原始值
            raw_cat_code = (item or {}).get("categoryCode")
            raw_cat_name = (item or {}).get("categoryName")
            raw_brand_code = (item or {}).get("brandCode")
            raw_brand_name = (item or {}).get("brandName")
            
            # 过滤掉无效的 categoryCode 值（"N/A", "NA", "NULL" 等）
            final_cat_code = raw_cat_code
            if final_cat_code:
                cat_code_str = str(final_cat_code).strip().upper()
                if cat_code_str in ("N/A", "NA", "NULL", "NONE", ""):
                    final_cat_code = None
            
            # 如果 categoryCode 无效，尝试使用传入的 category_code
            if not final_cat_code:
                final_cat_code = category_code
            
            # 过滤掉无效的 brandCode 值
            final_brand_code = raw_brand_code
            if final_brand_code:
                brand_code_str = str(final_brand_code).strip().upper()
                if brand_code_str in ("N/A", "NA", "NULL", "NONE", ""):
                    final_brand_code = None
            
            normalized.append({
                "categoryCode": final_cat_code,
                "categoryName": raw_cat_name or category_name,
                "brandCode": final_brand_code,
                "brandName": raw_brand_name,
            })
        
        # 限制返回数量，避免一次性返回过多内容
        if len(normalized) > self.max_results:
            log_debug(
                f"真实数据接口查询结果数量 {len(normalized)} 超过最大限制 {self.max_results}，已截断为前 {self.max_results} 条",
                log_level=1
            )
            normalized = normalized[: self.max_results]

        # 从接口返回结果互补 code / name（调用时可能只传其中一个）
        effective_code = category_code
        effective_name = category_name
        if normalized:
            first = normalized[0]
            if not effective_code:
                effective_code = first.get('categoryCode') or None
            if not effective_name:
                effective_name = first.get('categoryName') or None

        # 组合日志标签：有 code+name 则 "010202（空调）"，否则各自单独
        if effective_code and effective_name:
            query_label = f"{effective_code}（{effective_name}）"
        else:
            query_label = effective_name or effective_code
        log_info(f"查询商品库 | 查询：{query_label} | 对应品牌数：{len(normalized)}")
        
        # log_debug(f"查询分类关联品牌完成 | 分类: {query_label} | 返回 {len(normalized)} 个品牌", log_level=1)
        # log_debug(f"数据查询成功 | 分类: {query_label} | 返回 {len(normalized)} 个品牌")
        return normalized

    # ---------------------------- internal utils --------------------------- #
    def _post(self, path: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        headers = {"Content-Type": "application/json"}

        log_debug(f"请求 AI Trim 接口: {url} payload={payload}", log_level=1)  # 普通调试日志，使用1级
        
        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
        except requests.exceptions.SSLError:
            error_msg = f"SSL连接失败，无法访问接口: {url}"
            log_error(error_msg)
            raise RuntimeError(error_msg)
        except requests.exceptions.Timeout:
            error_msg = f"请求超时（{self.timeout}秒）: {url}"
            log_error(error_msg)
            raise RuntimeError(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = f"连接失败，无法访问接口: {url}"
            log_error(error_msg)
            raise RuntimeError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"请求异常: {url}"
            log_error(error_msg)
            raise RuntimeError(error_msg)
        
        # 处理HTTP错误状态码
        if resp.status_code != 200:
            error_detail = self._parse_error_response(resp, url, payload)
            log_error(f"接口请求失败: {error_detail}")
            raise RuntimeError(error_detail)
        
        # 解析响应体
        try:
            body = resp.json()
        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"接口响应不是有效的JSON格式: {url} - 响应内容: {resp.text[:200]}"
            log_error(error_msg)
            raise ValueError(error_msg) from e
        
        if not isinstance(body, dict):
            error_msg = f"接口响应格式异常，期望 dict，实际 {type(body)}: {body}"
            log_error(error_msg)
            raise ValueError(error_msg)

        if not body.get("success", False):
            code = body.get("code")
            desc = body.get("desc", "")
            error_msg = f"接口返回失败 code={code} desc={desc}"
            log_error(error_msg)
            raise RuntimeError(error_msg)

        data = body.get("data", None)
        if data is None:
            data = body.get("result", [])
        if data is None:
            log_warning(f"接口返回的 data 和 result 字段均为空: {url}")
            return []
        if not isinstance(data, list):
            error_msg = f"接口 data/result 字段期望 list，实际 {type(data)}: {data}"
            log_error(error_msg)
            raise ValueError(error_msg)
        return data
    
    def _parse_error_response(self, resp: requests.Response, url: str, payload: Dict[str, Any]) -> str:
        """
        解析错误响应，生成详细的错误信息
        
        Args:
            resp: HTTP响应对象
            url: 请求URL
            payload: 请求载荷
            
        Returns:
            格式化的错误信息字符串
        """
        status_code = resp.status_code
        error_parts = [f"HTTP {status_code} 错误"]
        
        # 尝试解析响应体
        try:
            error_body = resp.json()
            if isinstance(error_body, dict):
                error_msg = error_body.get("message") or error_body.get("error") or error_body.get("desc", "")
                if error_msg:
                    error_parts.append(f"错误信息: {error_msg}")
        except (json.JSONDecodeError, ValueError):
            # 如果不是JSON，尝试读取文本
            error_text = resp.text[:500]  # 限制长度
            if error_text:
                error_parts.append(f"响应内容: {error_text}")
        
        # 针对不同状态码提供特定提示
        if status_code == 404:
            error_parts.append(f"接口路径不存在: {url}")
            error_parts.append("可能的原因：")
            error_parts.append("  1. 接口路径配置错误")
            error_parts.append("  2. API服务未部署或路径已变更")
            error_parts.append(f"  3. 请检查 base_url 配置: {self.base_url}")
        elif status_code == 400:
            error_parts.append("请求参数错误")
            error_parts.append(f"请求载荷: {payload}")
        elif status_code == 401:
            error_parts.append("认证失败，请检查API密钥或权限")
        elif status_code == 403:
            error_parts.append("访问被拒绝，请检查权限配置")
        elif status_code == 500:
            error_parts.append("服务器内部错误，请稍后重试或联系技术支持")
        elif status_code >= 500:
            error_parts.append("服务器错误，请稍后重试")
        else:
            error_parts.append(f"未知错误状态码: {status_code}")
        
        return "\n".join(error_parts)

    # ----------------------- enrichment helpers --------------------------- #
    def _lookup_brand_code_by_category(self, category_code: str, brand_name: str) -> Optional[str]:
        """
        当 queryCategoryByBrand 返回的 brandCode 为空时，通过分类反查品牌列表以补全 brandCode。
        """
        cache_key = (category_code, brand_name)
        if cache_key in self._brand_code_cache:
            return self._brand_code_cache[cache_key]

        payload = {
            "categoryCode": category_code,
            "categoryName": None,
            "brandCode": None,
            "brandName": None,
        }
        try:
            brands = self._post("/queryBrandByCategory", payload)
            code: Optional[str] = None
            for item in brands:
                if (item or {}).get("brandName") == brand_name:
                    code = (item or {}).get("brandCode")
                    break
            self._brand_code_cache[cache_key] = code
            return code
        except Exception as e:  # noqa: BLE001
            log_warning(f"补全 brandCode 失败 category={category_code} brandName={brand_name} err={e}")
            self._brand_code_cache[cache_key] = None
            return None


def create_brand_category_api_toolkit(
    base_url: str = "https://api-show.haoxiny.com/open/api/aiTrim",
    timeout: float = 8.0,
    session: Optional[requests.Session] = None,
    max_results: int = 50,
    **kwargs: Any,
) -> BrandCategoryApiToolkit:
    """
    工厂函数，便于在 Agent 中创建并注册工具。
    
    Args:
        base_url: 服务基础地址
        timeout: HTTP 请求超时时间（秒）
        session: 可注入自定义 requests.Session
        max_results: 最大返回结果数量，默认50
    """
    return BrandCategoryApiToolkit(
        base_url=base_url,
        timeout=timeout,
        session=session,
        max_results=max_results,
        **kwargs,
    )


__all__ = [
    "BrandCategoryApiToolkit",
    "create_brand_category_api_toolkit",
]
