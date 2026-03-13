"""
工具调用钩子模块 - 用于记录所有工具的调用信息

通过Agno框架的tool_hooks机制，统一捕获所有工具调用（包括自定义工具和内置工具包），
在工具调用完成后记录日志（DEBUG级别，level=2）。

参考：Agno框架的tool_hooks参数，在Agent初始化时传入钩子函数。
"""

from __future__ import annotations

import json
import time
from contextvars import ContextVar
from typing import Any, Callable, Dict, List, Optional

from agno.utils.log import log_debug, log_info, log_warning

try:
    from utils.workflow_controller import (
        advance_stage_by_tool,
        ensure_retry_allowed_before_category_search,
        save_latest_build_review_fields_result,
    )
except ImportError:
    from pathlib import Path
    import sys

    _parent = Path(__file__).resolve().parents[1]
    if str(_parent) not in sys.path:
        sys.path.insert(0, str(_parent))
    from utils.workflow_controller import (
        advance_stage_by_tool,
        ensure_retry_allowed_before_category_search,
        save_latest_build_review_fields_result,
    )

# 当前请求「查询商品库阶段」结束时刻（perf_counter），供中间件在首包时计算「阶段结束→首包」耗时
_query_phase_end_time: ContextVar[Optional[float]] = ContextVar(
    "query_phase_end_time", default=None
)

# 当前 run 内「筛选后的节日」列表，供模型在第二阶段写入、第六阶段 build_review_fields 读取
_matched_festival_scenes: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar(
    "matched_festival_scenes", default=None
)


def set_matched_festival_scenes(scenes: Optional[List[Dict[str, Any]]]) -> None:
    """写入当前 run 的筛选后节日列表（供 save_matched_festivals 与 tool_hook 清空使用）。"""
    _matched_festival_scenes.set(scenes)


def get_matched_festival_scenes() -> Optional[List[Dict[str, Any]]]:
    """读取当前 run 的筛选后节日列表（供 build_review_fields 在未显式传入 festival_scenes 时使用）。"""
    try:
        return _matched_festival_scenes.get()
    except LookupError:
        return None

def log_time_to_first_token_post_hook(run_output: Any) -> None:
    """
    每条消息（每次 run）结束后打一条首字响应时间统计。
    使用 RunOutput.metrics.time_to_first_token（Agno 在 run 结束后填充）；无则记「无」。
    与用户是否确认推荐无关，确不确认都视作一条消息，均打一行。
    """
    try:
        metrics = getattr(run_output, "metrics", None)
        ttft: Optional[Any] = None
        if metrics is not None:
            ttft = getattr(metrics, "time_to_first_token", None)
            if ttft is None and hasattr(metrics, "to_dict"):
                try:
                    d = metrics.to_dict()
                    if isinstance(d, dict):
                        ttft = d.get("time_to_first_token")
                except Exception:
                    pass
        run_id = getattr(run_output, "run_id", None)
        session_id = getattr(run_output, "session_id", None)
        if ttft is not None:
            log_info(
                f"首字响应时间 | time_to_first_token：{ttft}s"
            )
        else:
            log_info(
                f"首字响应时间 | time_to_first_token：无"
            )
    except Exception:
        log_info("首字响应时间 | time_to_first_token：读取失败")


def _format_arguments(args: Dict[str, Any], max_length: int = 200) -> str:
    """
    格式化工具参数，避免输出过长
    
    Args:
        args: 工具参数字典
        max_length: 最大输出长度
        
    Returns:
        格式化后的参数字符串
    """
    if not args:
        return "{}"
    
    try:
        # 尝试转换为JSON字符串
        args_str = json.dumps(args, ensure_ascii=False, default=str)
        if len(args_str) <= max_length:
            return args_str
        
        # 如果过长，截断并添加省略号
        return args_str[:max_length] + "..."
    except Exception:
        # 如果转换失败，使用repr
        args_repr = repr(args)
        if len(args_repr) <= max_length:
            return args_repr
        return args_repr[:max_length] + "..."


def _format_result(result: Any, max_length: int = 300) -> str:
    """
    格式化工具执行结果，避免输出过长
    
    Args:
        result: 工具执行结果
        max_length: 最大输出长度
        
    Returns:
        格式化后的结果字符串
    """
    if result is None:
        return "None"
    
    # 如果是字符串，直接使用
    if isinstance(result, str):
        if len(result) <= max_length:
            return result
        return result[:max_length] + "..."
    
    # 如果是字典或列表，尝试转换为JSON
    if isinstance(result, (dict, list)):
        try:
            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) <= max_length:
                return result_str
            return result_str[:max_length] + "..."
        except Exception:
            pass
    
    # 其他类型使用repr
    result_repr = repr(result)
    if len(result_repr) <= max_length:
        return result_repr
    return result_repr[:max_length] + "..."


def log_tool_call_after(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    result: Any = None,
    error: Optional[Exception] = None,
    execution_time: Optional[float] = None,
) -> None:
    """
    工具调用后的钩子函数 - 记录工具调用信息
    
    Args:
        tool_name: 工具名称
        arguments: 工具调用参数
        result: 工具执行结果
        error: 执行错误（如果有）
        execution_time: 执行时间（秒）
    """
    # 格式化参数和结果
    args_str = _format_arguments(arguments or {})
    result_str = _format_result(result)
    
    # 构建日志消息
    status = "失败" if error else "成功"
    time_info = f" | 耗时: {execution_time:.3f}s" if execution_time is not None else ""
    error_info = f" | 错误: {str(error)}" if error else ""
    
    log_message = (
        f"[TOOL_CALL] 工具: {tool_name} | "
        f"状态: {status}{time_info} | "
        f"参数: {args_str} | "
        f"结果: {result_str}{error_info}"
    )
    
    log_debug(log_message, log_level=2)


def set_query_phase_end_time(t: float) -> None:
    """设置「查询商品库阶段」结束时刻（perf_counter），供首包耗时统计使用。"""
    _query_phase_end_time.set(t)


def get_and_clear_query_phase_end_time() -> Optional[float]:
    """获取并清除「查询商品库阶段」结束时刻，用于计算阶段结束到首包耗时。返回 None 表示未设置。"""
    try:
        t = _query_phase_end_time.get()
        if t is not None:
            _query_phase_end_time.set(None)
        return t
    except LookupError:
        return None


def create_tool_hook() -> Callable:
    """
    创建工具调用钩子函数
    
    返回一个符合Agno框架tool_hooks参数要求的钩子函数。
    钩子函数会在工具调用前后执行，记录工具调用信息。
    
    钩子函数签名：
        function_name: str - 工具名称
        function_call: Callable - 工具函数
        arguments: Dict[str, Any] - 工具参数
        
    Returns:
        钩子函数
    """
    # 节日阶段：首次/末次节日类工具调用的起止时间
    festival_stats: Dict[str, Optional[float]] = {
        'start_time': None,
        'end_time': None,
    }
    # 品类标准化阶段：统计整个阶段耗时（首次 search_category_by_name 到末次调用结束）
    category_norm_stats: Dict[str, Any] = {
        'start_time': None,
        'end_time': None,
    }
    # 本轮对话各次「品类标准化」阶段耗时（ms），用于最终汇总
    category_norm_phase_durations_ms: List[float] = []
    # 查询商品库阶段：按轮统计，每轮阶段时长（秒）从进入该轮 query 到该轮最后一次 query 返回的墙钟
    query_phase_rounds: List[float] = []
    seen_search_after_last_query: bool = False
    query_stats = {
        'query_brand_by_category': {
            'count': 0,
            'total_brands': 0,
            'categories': [],
            'start_time': None,  # 当前轮阶段开始时刻（墙钟）
            'end_time': None,  # 当前轮最后一次 query 结束时刻（墙钟）
            'total_execution_time': 0.0,  # 各次 query 耗时累加（秒）
        }
    }
    # 节日阶段涉及的工具名
    _festival_tool_names = ('get_festival_date_info', 'get_all_festivals', 'get_festivals_nearby')
    # LLM 推理时间估算 & 整合输出阶段 & think 调用统计
    llm_time_stats: Dict[str, Any] = {
        'run_start_time': None,       # 本次 run 第一个工具调用时刻（perf_counter）
        'total_tool_execution_s': 0.0,  # 所有工具纯执行时间累加（秒）
        'think_call_count': 0,        # think 工具调用次数
        'output_phase_start': None,   # build_review_fields 入 hook 时刻（perf_counter）
    }

    def tool_hook(function_name: str, function_call: Callable, arguments: Dict[str, Any], fc: Optional[Any] = None) -> Any:
        """
        工具调用钩子函数

        Args:
            function_name: 工具名称
            function_call: 工具函数
            arguments: 工具参数字典
            fc: FunctionCall 对象（由 Agno 框架自动注入，用于修改 fc.arguments 影响实际执行参数）

        Returns:
            工具执行结果
        """
        nonlocal seen_search_after_last_query
        start_time = time.perf_counter()
        error = None
        result = None

        # 品类标准化阶段：首次进入 query_brand_by_category 时，若已有品类标准化统计则仅记录本轮耗时并重置（最终在阶段耗时汇总中体现）
        if function_name == 'query_brand_by_category':
            if category_norm_stats['start_time'] is not None and category_norm_stats['end_time'] is not None:
                phase_duration_s = category_norm_stats['end_time'] - category_norm_stats['start_time']
                category_norm_phase_durations_ms.append(phase_duration_s * 1000)
                category_norm_stats['start_time'] = None
                category_norm_stats['end_time'] = None
            # 查询商品库多轮：若回退后再次进入本阶段，先保存上一轮阶段时长再重置
            stats = query_stats['query_brand_by_category']
            if seen_search_after_last_query and stats['start_time'] is not None:
                round_end = stats.get('end_time')
                round_duration_s = (round_end - stats['start_time']) if round_end is not None else 0.0
                if round_duration_s > 0:
                    query_phase_rounds.append(round_duration_s)
                query_stats['query_brand_by_category'] = {
                    'count': 0,
                    'total_brands': 0,
                    'categories': [],
                    'start_time': None,
                    'end_time': None,
                    'total_execution_time': 0.0,
                }
                seen_search_after_last_query = False

        # 查询商品库阶段：build_review_fields 表示阶段结束，按阶段各打一条 INFO
        if function_name == 'build_review_fields' and query_stats['query_brand_by_category']['count'] > 0:
            # 1. 节日阶段（一条 INFO）
            if festival_stats['start_time'] is not None and festival_stats['end_time'] is not None:
                festival_duration_s = festival_stats['end_time'] - festival_stats['start_time']
                log_info(f"节日场景阶段: {festival_duration_s:.2f}s")
                festival_stats['start_time'] = None
                festival_stats['end_time'] = None
            # 1.5. 节日匹配结果已在 save_matched_festivals 执行后实时打印，此处不再重复
            # 2. 品类标准化阶段（一条 INFO，括号内为各次耗时，单位：秒）
            if category_norm_phase_durations_ms:
                total_norm_s = sum(category_norm_phase_durations_ms) / 1000
                brackets = "、".join(f"第{i}次 {d/1000:.2f}s" for i, d in enumerate(category_norm_phase_durations_ms, 1))
                log_info(f"品类标准化阶段: {total_norm_s:.2f}s({brackets})")
                category_norm_phase_durations_ms.clear()
            # 3. 查询商品库阶段（总耗时=各轮阶段时间之和，括号内=每轮阶段时间，单位：秒）
            stats = query_stats['query_brand_by_category']
            last_round_s = 0.0
            if stats['start_time'] is not None and stats.get('end_time') is not None:
                last_round_s = stats['end_time'] - stats['start_time']
            all_rounds = query_phase_rounds + ([last_round_s] if last_round_s > 0 else [])
            total_s = sum(query_phase_rounds) + last_round_s
            brackets = "、".join(f"第{i}次 {r:.2f}s" for i, r in enumerate(all_rounds, 1)) if all_rounds else "0.00s"
            log_info(f"查询商品库阶段: {total_s:.2f}s({brackets})")
            set_query_phase_end_time(time.perf_counter())
            query_phase_rounds.clear()
            query_stats['query_brand_by_category'] = {
                'count': 0,
                'total_brands': 0,
                'categories': [],
                'start_time': None,
                'end_time': None,
                'total_execution_time': 0.0,
            }

        # 进入节日阶段时清空「筛选后节日」存储，避免上一轮残留；同时重置 LLM 时间统计
        if function_name == 'get_all_festivals':
            set_matched_festival_scenes(None)
            llm_time_stats['run_start_time'] = None
            llm_time_stats['total_tool_execution_s'] = 0.0
            llm_time_stats['think_call_count'] = 0
            llm_time_stats['output_phase_start'] = None

        # LLM 时间统计：记录本次 run 第一个工具调用时刻
        if llm_time_stats['run_start_time'] is None:
            llm_time_stats['run_start_time'] = start_time

        # 整合输出阶段：记录 build_review_fields 入 hook 时刻
        if function_name == 'build_review_fields':
            llm_time_stats['output_phase_start'] = start_time

        if function_name == 'search_category_by_name':
            ensure_retry_allowed_before_category_search()

        # analyze 工具的 result 参数要求为 str；若模型/框架传入 dict（如 build_review_fields 的返回值被解析为对象），则转为 JSON 字符串
        # 同时处理 result 与 recommendations，避免框架/模型使用不同参数名时仍传入 dict
        # 注意：execute_entrypoint 忽略 next_func 的 kwargs，直接用 fc.arguments（Pydantic BaseModel 属性）
        # 必须使用原地修改（fc.arguments[key] = ...）而非重建字典赋值，确保 execute_entrypoint 看到同一字典对象
        if function_name == 'analyze' and arguments:
            for key in ('result', 'recommendations'):
                val = arguments.get(key)
                if isinstance(val, (dict, list)):
                    try:
                        str_val = json.dumps(val, ensure_ascii=False, default=str)
                    except (TypeError, ValueError):
                        str_val = str(val)
                    arguments = {**arguments, key: str_val}
                    # 原地修改 fc.arguments 字典，保持对象引用不变
                    if fc is not None and hasattr(fc, 'arguments') and isinstance(fc.arguments, dict):
                        fc.arguments[key] = str_val

        try:
            result = function_call(**arguments)
            execution_time = time.perf_counter() - start_time

            log_tool_call_after(
                tool_name=function_name,
                arguments=arguments,
                result=result,
                error=None,
                execution_time=execution_time,
            )

            # 节日阶段：记录首次/末次节日类工具调用的起止时间
            if function_name in _festival_tool_names:
                if festival_stats['start_time'] is None:
                    festival_stats['start_time'] = start_time
                festival_stats['end_time'] = start_time + execution_time

            # save_matched_festivals 执行成功后立即打印节日匹配结果（此时品类标准化尚未开始，时序正确）
            if function_name == 'save_matched_festivals':
                scenes = get_matched_festival_scenes()
                if scenes:
                    names = [str(s.get("festival_name", "")) for s in scenes if s.get("festival_name")]
                    if names:
                        log_info(f"节日匹配：[{'，'.join(names)}]")
                else:
                    log_info("节日匹配：无")

            advance_stage_by_tool(function_name)

            # 品类标准化：记录阶段起止时间（首次调用记 start，每次调用结束记 end）
            if function_name == 'search_category_by_name':
                if category_norm_stats['start_time'] is None:
                    category_norm_stats['start_time'] = start_time
                category_norm_stats['end_time'] = start_time + execution_time
                seen_search_after_last_query = True

            # 查询商品库：记录阶段开始时刻、该轮结束时刻并累加各次 query 的耗时
            if function_name == 'query_brand_by_category' and result is not None:
                stats = query_stats['query_brand_by_category']
                if stats['start_time'] is None:
                    stats['start_time'] = start_time
                stats['end_time'] = start_time + execution_time
                stats['count'] += 1
                stats['total_execution_time'] += execution_time
                if isinstance(result, list):
                    stats['total_brands'] += len(result)
                    category_name = arguments.get('category_name') or arguments.get('category_code', '未知')
                    stats['categories'].append(category_name)

            # LLM 时间统计：累加所有工具纯执行时间，统计 think 调用次数
            llm_time_stats['total_tool_execution_s'] += execution_time
            if function_name == 'think':
                llm_time_stats['think_call_count'] += 1

            # analyze 完成后：按顺序打印 think 次数、整合输出阶段、LLM 推理时间估算
            if function_name == 'analyze':
                think_count = llm_time_stats['think_call_count']
                log_info(f"think 累计调用: {think_count}次")
                if llm_time_stats['output_phase_start'] is not None:
                    output_duration_s = (start_time + execution_time) - llm_time_stats['output_phase_start']
                    log_info(f"整合输出阶段: {output_duration_s:.2f}s")
                if llm_time_stats['run_start_time'] is not None:
                    run_wall_s = (start_time + execution_time) - llm_time_stats['run_start_time']
                    llm_estimated_s = run_wall_s - llm_time_stats['total_tool_execution_s']
                    if llm_estimated_s > 0:
                        log_info(f"LLM 推理时间（估算）: {llm_estimated_s:.1f}s")
                # 重置，供下次 run 使用
                llm_time_stats['run_start_time'] = None
                llm_time_stats['total_tool_execution_s'] = 0.0
                llm_time_stats['think_call_count'] = 0
                llm_time_stats['output_phase_start'] = None

            if function_name == 'build_review_fields' and isinstance(result, str):
                save_latest_build_review_fields_result(result)

            return result

        except Exception as e:
            execution_time = time.perf_counter() - start_time
            error = e
            log_tool_call_after(
                tool_name=function_name,
                arguments=arguments,
                result=None,
                error=error,
                execution_time=execution_time,
            )
            raise
    return tool_hook


__all__ = [
    "log_tool_call_after",
    "create_tool_hook",
    "set_query_phase_end_time",
    "get_and_clear_query_phase_end_time",
    "log_time_to_first_token_post_hook",
    "set_matched_festival_scenes",
    "get_matched_festival_scenes",
]
