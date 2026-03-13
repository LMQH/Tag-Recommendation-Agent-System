"""
查询标准化工具包 - 封装 Milvus 向量搜索与 QwenRerank 精排能力

功能：
- 根据品类名称搜索标准化的品类编码和名称
- 支持 Embedding 向量化 → Milvus 召回 → Qwen Rerank 精排
- 双重降级策略：向量搜索失败时自动降级为直接查询
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from agno.tools import Toolkit
from agno.utils.log import log_info, log_debug, log_warning, log_error, log_exception

# 添加项目根目录到 Python 路径
_THIS_FILE = os.path.abspath(__file__)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from search_data.milvus_category_store import CategoryCandidate, MilvusCategoryStore
from search_data.qwen_client import QwenEmbeddingClient, QwenRerankClient
from search_data.config import QWEN_RERANK_INSTRUCT_CATEGORY



class QueryNormalizationToolkit(Toolkit):
    """
    查询标准化工具包

    封装 Milvus 向量搜索和 QwenRerank 精排能力，提供品类名称标准化功能。
    支持双重降级策略，确保向量搜索失败时不影响主流程。
    """

    def __init__(
        self,
        milvus_host: Optional[str] = None,
        milvus_port: Optional[int] = None,
        milvus_db_name: Optional[str] = None,
        qwen_api_key: Optional[str] = None,
        qwen_base_url: Optional[str] = None,
        qwen_rerank_base_url: Optional[str] = None,
        qwen_rerank_path: Optional[str] = None,
        qwen_rerank_model: Optional[str] = None,
        enable_rerank: bool = True,
        timeout: int = 30,
        **kwargs
    ):
        """
        初始化查询标准化工具包

        Args:
            milvus_host: Milvus 服务器地址（从配置读取）
            milvus_port: Milvus 服务器端口（从配置读取）
            milvus_db_name: Milvus 数据库名称
            qwen_api_key: Qwen API Key（从配置读取）
            qwen_base_url: Qwen Embedding API 地址（从配置读取）
            qwen_rerank_base_url: Qwen Rerank API 基础地址（从配置读取）
            qwen_rerank_path: Qwen Rerank API 路径（从配置读取）
            qwen_rerank_model: Qwen Rerank 模型名称（从配置读取）
            enable_rerank: 是否启用 Rerank 精排（默认True）
            timeout: Rerank 超时时间（秒）
        """
        super().__init__(
            name="query_normalization_toolkit",
            tools=[self.search_category_by_name],
            **kwargs
        )

        # 初始化 Milvus 品类存储
        self.milvus_category_store = MilvusCategoryStore(
            host=milvus_host,
            port=milvus_port,
            db_name=milvus_db_name
        )

        # 初始化 Qwen Embedding 客户端
        self.qwen_embedding_client = QwenEmbeddingClient(
            api_key=qwen_api_key,
            base_url=qwen_base_url
        )

        # 从配置读取默认参数（如果未在参数中指定）
        try:
            from config.config_loader import get_query_normalization_config
            query_norm_config = get_query_normalization_config()
            # 如果enable_rerank未指定，使用配置值
            if enable_rerank is None:
                enable_rerank = query_norm_config.get("enable_rerank", True)
            # 如果timeout未指定，使用配置值
            if timeout is None:
                timeout = query_norm_config.get("timeout", 30)
            self._default_top_k = query_norm_config.get("top_k", 100)
            self._default_top_n = query_norm_config.get("top_n", 3)

            # 新增：加载智能rerank配置
            self._vector_score_threshold = query_norm_config.get("vector_score_threshold", 0.85)
            self._min_high_score_count = query_norm_config.get("min_high_score_count", 3)
            self._use_smart_rerank = query_norm_config.get("use_smart_rerank", True)
        except Exception as e:
            log_warning(f"无法加载查询标准化配置，使用默认值: {e}")
            if enable_rerank is None:
                enable_rerank = True
            if timeout is None:
                timeout = 30
            self._default_top_k = 100
            self._default_top_n = 3
            # 新增：使用默认值
            self._vector_score_threshold = 0.85
            self._min_high_score_count = 3
            self._use_smart_rerank = True

        # 初始化 Qwen Rerank 客户端（可选）
        self.qwen_rerank_client = None
        if enable_rerank:
            self.qwen_rerank_client = QwenRerankClient(
                api_key=qwen_api_key,
                base_url=qwen_rerank_base_url,
                path=qwen_rerank_path,
                model=qwen_rerank_model,
                instruct=QWEN_RERANK_INSTRUCT_CATEGORY,
                timeout_s=timeout
            )

        self.enable_rerank = enable_rerank
        self.timeout = timeout

        log_debug(
            f"查询标准化工具包初始化完成，Rerank: {self.enable_rerank}, "
            f"TopK: {self._default_top_k}, TopN: {self._default_top_n}, "
            f"智能Rerank: {self._use_smart_rerank}, 阈值: {self._vector_score_threshold}",
            log_level=1
        )  # 普通调试日志，使用1级

    def search_category_by_name(
        self,
        category_name: str,
        top_k: Optional[int] = None,
        top_n: Optional[int] = None,
        enable_rerank: Optional[bool] = None,
        category_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据品类名称搜索标准化的品类编码和名称（向量搜索 + Rerank）

        Args:
            category_name: 用户输入的品类名称（如"厨房电器"、"手机"、"厨电"等）
            top_k: 向量召回数量（如果为None则使用实例配置或默认200）
            top_n: 最终返回数量（如果为None则使用实例配置或默认12）
            enable_rerank: 是否启用 Rerank 精排（如果为None则使用实例配置或默认True）
            category_level: 品类层级过滤（"1"/"2"/"3"/None=全部）

        Returns:
            {
                "success": True/False,
                "query": "用户原始查询",
                "normalized_results": [
                    {
                        "category_code": "L1_L2_L3",
                        "category_name": "标准品类名称",
                        "category_level": 3,
                        "l1_name": "一级品类",
                        "l2_name": "二级品类",
                        "l3_name": "三级品类",
                        "path_name": "完整路径",
                        "vector_score": 0.85,
                        "rerank_score": 0.92
                    },
                    ...
                ],
                "fallback_used": False,  # 是否使用了降级策略
                "message": "搜索成功"
            }

        降级情况：
            当向量搜索失败时，返回：
            {
                "success": True,
                "normalized_results": [{
                    "category_code": "",  # 空编码表示降级
                    "category_name": category_name,  # 原始名称
                    "vector_score": 0.0,
                    "rerank_score": None
                }],
                "fallback_used": True,
                "message": "向量搜索失败，已降级为直接查询"
            }
        """
        # 参数校验
        if not category_name or not category_name.strip():
            return {
                "success": False,
                "query": category_name,
                "normalized_results": [],
                "fallback_used": False,
                "message": "品类名称不能为空"
            }

        # 使用传入参数或实例配置的默认值
        final_top_k = top_k if top_k is not None else getattr(self, '_default_top_k', 200)
        final_top_n = top_n if top_n is not None else getattr(self, '_default_top_n', 3)
        final_enable_rerank = enable_rerank if enable_rerank is not None else self.enable_rerank

        try:
            # 1. Embedding 向量化
            log_debug(f"开始品类标准化搜索: {category_name}", log_level=1)  # 普通调试日志，使用1级
            query_vector = self.qwen_embedding_client.embed_text(category_name)
            log_debug(f"Embedding 完成，向量维度: {len(query_vector)}", log_level=1)  # 普通调试日志，使用1级

            # 2. Milvus 向量召回
            expr = self._build_expr(category_level)
            candidates = self.milvus_category_store.search(
                query_vector=query_vector,
                topk=final_top_k,
                expr=expr
            )
            if not candidates:
                log_warning(f"Milvus 未找到匹配品类，启用降级策略")
                return self._build_fallback_result(
                    category_name=category_name,
                    reason="Milvus 未找到匹配品类"
                )

            # 3. Rerank 精排（如果启用）
            should_rerank = final_enable_rerank and self.qwen_rerank_client
            if should_rerank:
                # 新增：智能rerank策略判断
                if self._use_smart_rerank:
                    # 检查是否满足跳过rerank的条件
                    skip_rerank = self._should_skip_rerank(candidates[:final_top_k])

                    if skip_rerank:
                        log_info(
                            f"向量分数足够高，跳过Rerank | Top1分数: {candidates[0].vector_score:.4f} | "
                            f"阈值: {self._vector_score_threshold}"
                        )
                        # 直接按向量分数排序，不使用rerank
                        ranked = self._candidates_to_dict(candidates[:final_top_n])
                    else:
                        log_debug(f"开始 Rerank 精排，候选数量: {min(final_top_k, len(candidates))}", log_level=1)
                        ranked = self._rerank_categories(
                            query=category_name,
                            candidates=candidates[:final_top_k]
                        )
                else:
                    # 使用原有全量rerank逻辑
                    log_debug(f"开始 Rerank 精排（全量模式），候选数量: {min(final_top_k, len(candidates))}", log_level=1)
                    ranked = self._rerank_categories(
                        query=category_name,
                        candidates=candidates[:final_top_k]
                    )
            else:
                # 不使用 Rerank，直接按向量分数排序
                ranked = self._candidates_to_dict(candidates[:final_top_n])

            # 4. 返回 TopN 结果
            final_results = ranked[:final_top_n]
            recall_part = f"召回 {len(candidates)}/{final_top_k}"
            rerank_part = f"重排序 {len(final_results)}/{final_top_n}"
            log_info(
                f"品类标准化 | 搜索: {category_name} | {recall_part} | {rerank_part}"
            )

            return {
                "success": True,
                "query": category_name,
                "normalized_results": final_results,
                "fallback_used": False,
                "message": f"已匹配到共计 {len(final_results)} 个标准化品类"
            }

        except Exception as e:
            log_exception(f"品类向量搜索失败: {e}")
            # 工具层降级：返回原始名称，让后续 API 工具处理
            return self._build_fallback_result(
                category_name=category_name,
                reason=f"向量搜索异常: {str(e)}"
            )

    def _build_expr(self, category_level: Optional[str]) -> str:
        """构建 Milvus 过滤表达式"""
        expr_parts = ["is_deleted == 0 && is_enabled == 1"]
        if category_level:
            try:
                level_int = int(category_level)
                expr_parts.append(f"category_level == {level_int}")
            except ValueError:
                log_warning(f"无效的品类层级: {category_level}，忽略层级过滤")
        return " && ".join(expr_parts)

    def _should_skip_rerank(self, candidates: List[CategoryCandidate]) -> bool:
        """
        判断是否应该跳过Rerank精排

        策略：
        1. 检查前N个候选的向量分数
        2. 如果最高分 ≥ 阈值，且至少有 min_high_score_count 个结果 ≥ 阈值，则跳过rerank
        3. 否则执行rerank

        Args:
            candidates: Milvus召回的候选品类列表

        Returns:
            True: 跳过rerank，直接使用向量分数排序
            False: 执行rerank精排
        """
        if not candidates:
            return False

        # 检查最高分
        max_score = candidates[0].vector_score

        # 如果最高分未达到阈值，必须rerank
        if max_score < self._vector_score_threshold:
            log_debug(
                f"最高分 {max_score:.4f} 低于阈值 {self._vector_score_threshold}，需要Rerank",
                log_level=2
            )
            return False

        # 统计达到阈值的候选数量
        high_score_count = sum(
            1 for c in candidates
            if c.vector_score >= self._vector_score_threshold
        )

        # 判断是否有足够的高分结果
        if high_score_count >= self._min_high_score_count:
            log_debug(
                f"发现 {high_score_count} 个高分结果（≥{self._vector_score_threshold}），"
                f"跳过Rerank以提升性能",
                log_level=2
            )
            return True

        log_debug(
            f"仅有 {high_score_count} 个高分结果，少于要求的 {self._min_high_score_count} 个，"
            f"执行Rerank以确保准确性",
            log_level=2
        )
        return False

    def _rerank_categories(self, query: str, candidates: List[CategoryCandidate]) -> List[Dict[str, Any]]:
        """
        使用 Qwen Rerank 对品类候选进行精排

        Args:
            query: 用户查询文本
            candidates: Milvus 召回的候选品类列表

        Returns:
            精排后的品类列表（已按 rerank_score 降序排序）
        """
        # 构造 Rerank 文档列表
        docs = [
            f"PATH={c.path_name}; CODE={c.category_code}; NAME={c.category_name}; "
            f"L1={c.l1_name}; L2={c.l2_name}; L3={c.l3_name}; LEVEL={c.category_level}"
            for c in candidates
        ]

        # 调用 Qwen Rerank API
        rerank_result = self.qwen_rerank_client.rerank(
            query=query,
            documents=docs
        )

        # 映射 rerank 分数到候选列表
        score_by_idx = {item.index: item.score for item in rerank_result.items}

        # 构造结果
        ranked = []
        for i, c in enumerate(candidates):
            ranked.append({
                "category_id": c.category_id,
                "category_code": c.category_code,
                "category_name": c.category_name,
                "category_level": c.category_level,
                "parent_code": c.parent_code,
                "l1_code": c.l1_code,
                "l1_name": c.l1_name,
                "l2_code": c.l2_code,
                "l2_name": c.l2_name,
                "l3_code": c.l3_code,
                "l3_name": c.l3_name,
                "path_name": c.path_name,
                "vector_score": c.vector_score,
                "rerank_score": score_by_idx.get(i)
            })

        # 按 rerank 分数降序排序
        ranked.sort(
            key=lambda x: (x["rerank_score"] is not None, x["rerank_score"] or -1.0),
            reverse=True
        )

        log_debug(f"Rerank 完成，Top3 分数: {[r.get('rerank_score') for r in ranked[:3]]}", log_level=1)  # 普通调试日志，使用1级
        return ranked

    def _candidates_to_dict(self, candidates: List[CategoryCandidate]) -> List[Dict[str, Any]]:
        """
        将候选列表转换为字典格式（无 Rerank，直接使用向量分数）

        Args:
            candidates: Milvus 召回的候选品类列表

        Returns:
            品类字典列表
        """
        return [
            {
                "category_id": c.category_id,
                "category_code": c.category_code,
                "category_name": c.category_name,
                "category_level": c.category_level,
                "parent_code": c.parent_code,
                "l1_code": c.l1_code,
                "l1_name": c.l1_name,
                "l2_code": c.l2_code,
                "l2_name": c.l2_name,
                "l3_code": c.l3_code,
                "l3_name": c.l3_name,
                "path_name": c.path_name,
                "vector_score": c.vector_score,
                "rerank_score": None
            }
            for c in candidates
        ]

    def _build_fallback_result(self, category_name: str, reason: str) -> Dict[str, Any]:
        """
        构造降级结果

        当向量搜索失败时，返回原始名称（空编码表示降级），
        让 Agent 层可以继续使用 category_name 调用后续 API。

        Args:
            category_name: 用户原始品类名称
            reason: 降级原因

        Returns:
            降级结果字典
        """
        return {
            "success": True,
            "query": category_name,
            "normalized_results": [{
                "category_code": "",  # 空编码表示降级
                "category_name": category_name,
                "category_level": None,
                "l1_name": None,
                "l2_name": None,
                "l3_name": None,
                "path_name": None,
                "vector_score": 0.0,
                "rerank_score": None
            }],
            "fallback_used": True,
            "message": f"向量搜索失败，已降级为直接查询。原因: {reason}"
        }


def create_query_normalization_toolkit(**kwargs) -> QueryNormalizationToolkit:
    """
    创建查询标准化工具包实例

    Args:
        **kwargs: 传递给 QueryNormalizationToolkit 的参数

    Returns:
        QueryNormalizationToolkit 实例

    示例:
        from ecom_reco_agent.config.config_loader import get_search_config

        search_config = get_search_config()
        toolkit = create_query_normalization_toolkit(
            milvus_host=search_config.get("milvus", {}).get("host"),
            milvus_port=search_config.get("milvus", {}).get("port"),
            qwen_api_key=search_config.get("qwen", {}).get("api_key"),
            qwen_base_url=search_config.get("qwen", {}).get("base_url"),
            enable_rerank=search_config.get("default_params", {}).get("enable_rerank", True),
            timeout=search_config.get("default_params", {}).get("timeout", 30)
        )
    """
    return QueryNormalizationToolkit(**kwargs)
