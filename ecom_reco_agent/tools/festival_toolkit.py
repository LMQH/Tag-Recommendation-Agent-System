"""
Festival Toolkit Module
节日工具包 - 统一管理节日相关功能
支持日期信息获取，以及数据库节日查询
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, List, Dict

from agno.tools import tool
from agno.utils.log import log_info, log_warning, log_error, log_debug

# 尝试导入农历库
try:
    from zhdate import ZhDate
    ZHDATE_AVAILABLE = True
except ImportError:
    ZHDATE_AVAILABLE = False
    log_warning("zhdate 库未安装，农历节日计算将使用简化方法。建议运行: pip install zhdate")

# 添加项目根目录到 Python 路径
_THIS_FILE = os.path.abspath(__file__)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from search_data.data.mysql_data_source import get_b2b_mysql_source

# 导入配置加载器
try:
    from config.config_loader import get_festival_tools_config
except ImportError:
    # 如果导入失败，尝试从相对路径导入
    from pathlib import Path
    config_path = Path(__file__).resolve().parents[1] / "config"
    if str(config_path) not in sys.path:
        sys.path.insert(0, str(config_path.parent))
    from config.config_loader import get_festival_tools_config


# ==================== 缓存机制 ====================

# 模块级缓存变量
_festival_cache: Dict[str, Any] = None


def _load_all_festivals() -> List[Dict[str, Any]]:
    """
    从数据库全量加载所有节日数据

    Returns:
        节日数据列表，包含所有字段
    """
    try:
        db = get_b2b_mysql_source()
        table_config = os.getenv("BUSINESS_TABLE_FESTIVAL", "skycrane_website.t_trim_festival_data")

        if '.' in table_config:
            full_table_name = table_config
        else:
            full_table_name = f"skycrane_website.{table_config}"
        
        query = f"""
        SELECT id, festival_name, scene_type
        FROM {full_table_name}
        """

        log_debug(f"执行节日数据全量加载查询: {query}", log_level=1)
        results = db.execute_query(query)
        log_debug(f"查询返回 {len(results) if results else 0} 条记录", log_level=1)
        
        if results:
            # 记录第一条数据，用于调试字段名
            log_debug(f"第一条数据示例: {results[0]}", log_level=1)
        else:
            log_warning("节日数据查询返回空结果，请检查数据库连接和数据表配置")
        
        return results if results else []
    except Exception as e:
        log_error(f"全量加载节日数据失败: {e}")
        import traceback
        log_error(f"详细错误信息: {traceback.format_exc()}")
        return []


def _is_cache_expired(cache: Dict[str, Any], refresh_interval_hours: int) -> bool:
    """
    检查缓存是否过期
    
    Args:
        cache: 缓存字典，包含 timestamp 字段
        refresh_interval_hours: 配置的刷新间隔（小时）
    
    Returns:
        True 如果缓存过期，False 否则
    """
    if cache is None:
        return True
    
    if "timestamp" not in cache:
        return True
    
    elapsed_hours = (datetime.now() - cache["timestamp"]).total_seconds() / 3600
    # TTL硬限制24小时，取配置值和24小时的最小值
    ttl_hours = min(24, refresh_interval_hours)
    
    return elapsed_hours >= ttl_hours


def _get_cached_festivals() -> List[Dict[str, Any]]:
    """
    获取缓存的节日数据，如果缓存过期则自动刷新
    
    Returns:
        节日数据列表
    """
    global _festival_cache
    
    try:
        # 获取配置
        config = get_festival_tools_config()
        refresh_interval_hours = config.get("cache_refresh_interval_hours", 24)
    except Exception as e:
        log_warning(f"读取节日工具配置失败: {e}，使用默认值24小时")
        refresh_interval_hours = 24
    
    # 检查缓存是否过期
    if _is_cache_expired(_festival_cache, refresh_interval_hours):
        log_info("节日数据缓存已过期，开始刷新...")
        try:
            data = _load_all_festivals()
            _festival_cache = {
                "data": data,
                "timestamp": datetime.now(),
                "ttl_hours": refresh_interval_hours
            }
            log_info(f"节日数据缓存刷新成功，共加载 {len(data)} 条记录")
        except Exception as e:
            log_error(f"刷新节日数据缓存失败: {e}")
            # 如果刷新失败，尝试使用旧缓存
            if _festival_cache and "data" in _festival_cache:
                log_warning("使用旧的缓存数据")
                return _festival_cache["data"]
            return []
    
    return _festival_cache.get("data", []) if _festival_cache else []


# ==================== 日期计算相关函数 ====================

def lunar_to_solar(year: int, month: int, day: int) -> datetime:
    """
    将农历日期转换为公历日期
    
    Args:
        year: 农历年份
        month: 农历月份
        day: 农历日期
    
    Returns:
        对应的公历日期
    """
    if ZHDATE_AVAILABLE:
        try:
            lunar_date = ZhDate(year, month, day)
            return lunar_date.to_datetime()
        except Exception as e:
            log_warning(f"农历转公历失败 ({year}-{month}-{day}): {e}，使用估算方法")
    
    # 如果 zhdate 不可用或转换失败，使用简化估算
    # 农历通常比公历晚约1个月
    estimated_month = month + 1
    estimated_day = day
    
    if estimated_month > 12:
        estimated_month = 1
        year += 1
    
    try:
        return datetime(year, estimated_month, estimated_day)
    except ValueError:
        # 如果日期无效（如2月30日），使用该月最后一天
        if estimated_month == 2:
            estimated_day = 28
        elif estimated_month in [4, 6, 9, 11]:
            estimated_day = 30
        else:
            estimated_day = 31
        return datetime(year, estimated_month, estimated_day)


# ==================== 数据库查询相关函数 ====================

def _fuzzy_query(
    database_name: str,
    table_name: str,
    search_field: str,
    keyword: str,
    return_fields: List[str]
) -> List[Dict[str, Any]]:
    """
    执行模糊查询

    Args:
        database_name: 数据库名称
        table_name: 表名（可以是 database.table 格式或单独的表名）
        search_field: 搜索字段名
        keyword: 搜索关键词
        return_fields: 需要返回的字段列表

    Returns:
        查询结果列表，每个元素是一个包含返回字段的字典
    """
    if not keyword:
        return []

    # 构建完整的表名
    if '.' not in table_name:
        full_table_name = f"{database_name}.{table_name}"
    else:
        full_table_name = table_name

    db = get_b2b_mysql_source()

    fields_str = ', '.join(return_fields)
    search_pattern = f"%{keyword}%"

    sql = f"""
        SELECT {fields_str}
        FROM {full_table_name}
        WHERE {search_field} LIKE %s
    """

    params = (search_pattern,)

    try:
        results = db.execute_query(sql, params=params)
        return results if results else []
    except Exception as e:
        log_error(f"查询节日数据失败: {e}")
        return []


# ==================== 工具函数（使用 @tool 装饰器） ====================

@tool
def get_festivals_nearby(days_ahead: int = 30) -> str:
    """
    获取当前时间信息，用于 Agent 智能推断可能的节日场景
    
    Args:
        days_ahead: 向前查找的天数，默认30天（用于说明查找范围）
    
    Returns:
        当前时间信息的文本描述，供 Agent 使用模型智能推断节日
    """
    current_date = datetime.now()
    
    result_parts = []
    result_parts.append(f"当前日期: {current_date.strftime('%Y年%m月%d日')}")
    result_parts.append(f"当前时间: {current_date.strftime('%H:%M:%S')}")
    result_parts.append(f"星期: 星期{'一二三四五六日'[current_date.weekday()]}")
    result_parts.append(f"月份: {current_date.month}月")
    result_parts.append(f"季节: {'春夏秋冬'[(current_date.month - 1) // 3]}季")
    
    if ZHDATE_AVAILABLE:
        try:
            lunar = ZhDate.from_datetime(current_date)
            result_parts.append(f"农历日期: {lunar.chinese()}")
        except Exception as e:
            log_warning(f"获取农历信息失败: {e}")
            result_parts.append(f"农历日期: 无法获取")
    else:
        result_parts.append(f"农历支持: 未安装 zhdate 库")
    
    result_parts.append(f"查找范围: 未来{days_ahead}天")
    
    return "\n".join(result_parts)


@tool
def get_festival_date_info() -> str:
    """
    获取当前日期时间信息，包含公历和农历信息
    
    Returns:
        当前日期时间的详细描述
    """
    now = datetime.now()
    result_parts = []
    
    result_parts.append("当前日期时间信息：")
    result_parts.append(f"- 公历日期: {now.strftime('%Y年%m月%d日')}")
    result_parts.append(f"- 星期: 星期{'一二三四五六日'[now.weekday()]}")
    result_parts.append(f"- 时间: {now.strftime('%H:%M:%S')}")
    
    # 添加农历信息
    if ZHDATE_AVAILABLE:
        try:
            lunar = ZhDate.from_datetime(now)
            result_parts.append(f"- 农历日期: {lunar.chinese()}")
        except Exception as e:
            log_warning(f"获取农历信息失败: {e}")
            result_parts.append(f"- 农历日期: 无法获取")
    else:
        result_parts.append(f"- 农历日期: 未安装 zhdate 库")
    
    result_parts.append(f"- 季节: {'春夏秋冬'[(now.month - 1) // 3]}季")
    result_parts.append(f"- 月份: {now.month}月")
    result_parts.append(f"- 年度第几天: {(now - datetime(now.year, 1, 1)).days + 1} 天")
    
    return "\n".join(result_parts)


# DEPRECATED: 保留待后续使用
@tool
def query_festival_by_name(keyword: str) -> str:
    """
    根据节日名称关键词查询节日数据信息表
    
    注意：此函数已废弃，建议使用 get_all_festivals() 获取所有节日数据，由模型进行筛选。

    Args:
        keyword: 搜索关键词，用于在festival_name字段中进行模糊匹配

    Returns:
        查询结果的字符串表示，包含id、festival_name、scene_type字段
    """
    table_config = os.getenv("BUSINESS_TABLE_FESTIVAL", "skycrane_website.t_trim_festival_data")

    if '.' in table_config:
        database_name, table_name = table_config.split('.', 1)
    else:
        database_name = "skycrane_website"
        table_name = table_config

    results = _fuzzy_query(
        database_name=database_name,
        table_name=table_name,
        search_field="festival_name",
        keyword=keyword,
        return_fields=["id", "festival_name", "scene_type"]
    )

    if not results:
        return "未找到匹配的节日数据"

    result_parts = []
    result_parts.append(f"找到 {len(results)} 条节日数据：\n")

    for i, record in enumerate(results, 1):
        result_parts.append(f"{i}. ID: {record.get('id', 'N/A')}")
        result_parts.append(f"   节日名称: {record.get('festival_name', 'N/A')}")
        result_parts.append(f"   场景类型: {record.get('scene_type', 'N/A')}")
        result_parts.append("")

    return "\n".join(result_parts)


# DEPRECATED: 保留待后续使用
@tool
def query_festivals_by_scene(keyword: str) -> str:
    """
    根据场景类型关键词查询节日数据信息表
    
    注意：此函数已废弃，建议使用 get_all_festivals() 获取所有节日数据，由模型进行筛选。

    Args:
        keyword: 搜索关键词，用于在scene_type字段中进行模糊匹配

    Returns:
        查询结果的字符串表示，包含id、festival_name、scene_type字段
    """
    table_config = os.getenv("BUSINESS_TABLE_FESTIVAL", "skycrane_website.t_trim_festival_data")

    if '.' in table_config:
        database_name, table_name = table_config.split('.', 1)
    else:
        database_name = "skycrane_website"
        table_name = table_config

    results = _fuzzy_query(
        database_name=database_name,
        table_name=table_name,
        search_field="scene_type",
        keyword=keyword,
        return_fields=["id", "festival_name", "scene_type"]
    )

    if not results:
        return "未找到匹配的节日数据"

    result_parts = []
    result_parts.append(f"找到 {len(results)} 条节日数据（按场景类型查询）：\n")

    for i, record in enumerate(results, 1):
        result_parts.append(f"{i}. ID: {record.get('id', 'N/A')}")
        result_parts.append(f"   节日名称: {record.get('festival_name', 'N/A')}")
        result_parts.append(f"   场景类型: {record.get('scene_type', 'N/A')}")
        result_parts.append("")

    return "\n".join(result_parts)


def _get_set_matched_festival_scenes():
    try:
        from utils.tool_hooks import set_matched_festival_scenes
        return set_matched_festival_scenes
    except ImportError:
        from pathlib import Path
        _parent = Path(__file__).resolve().parents[1]
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        from utils.tool_hooks import set_matched_festival_scenes
        return set_matched_festival_scenes


@tool
def save_matched_festivals(festival_scenes: Any) -> str:
    """
    保存筛选后的节日到会话变量，供后续阶段（含 build_review_fields）使用。

    在第二阶段根据用户意图与当前时间从 get_all_festivals 结果中筛选出匹配的节日后，
    应调用本工具将结果写入会话变量；第六阶段调用 build_review_fields 时若未显式传入
    festival_scenes，将自动使用此处保存的列表。

    Args:
        festival_scenes: 筛选后的节日列表，每项必须包含 id、festival_name、scene_type。
            可为 list 或 JSON 字符串，格式示例：[{"id": 1, "festival_name": "元宵", "scene_type": "节日营销"}]

    Returns:
        成功提示，如「已保存筛选后的节日，共 N 个」
    """
    set_matched_festival_scenes_fn = _get_set_matched_festival_scenes()
    if festival_scenes is None:
        set_matched_festival_scenes_fn(None)
        return "已清空筛选后的节日存储"
    if isinstance(festival_scenes, str):
        try:
            festival_scenes = json.loads(festival_scenes)
        except json.JSONDecodeError as e:
            return f"无法解析 JSON 字符串: {e}"
    if not isinstance(festival_scenes, list):
        return "festival_scenes 必须为列表或 JSON 数组字符串"
    if not festival_scenes:
        set_matched_festival_scenes_fn([])
        return "已保存筛选后的节日，共 0 个"
    required = ("id", "festival_name", "scene_type")
    for i, item in enumerate(festival_scenes):
        if not isinstance(item, dict):
            return f"第 {i + 1} 项必须为对象（含 id、festival_name、scene_type）"
        for k in required:
            if k not in item or item[k] is None or (isinstance(item[k], str) and not item[k].strip()):
                return f"第 {i + 1} 项缺少或为空字段: {k}"
    set_matched_festival_scenes_fn(festival_scenes)
    return f"已保存筛选后的节日，共 {len(festival_scenes)} 个"


@tool
def get_all_festivals() -> str:
    """
    获取所有节日数据，供模型基于当前时间和用户意图进行智能筛选
    
    此工具返回数据库中所有有效的节日数据（包含 id、festival_name、scene_type 字段），
    模型应基于 get_festival_date_info() 返回的当前时间信息，以及用户的问题意图，
    从这些数据中筛选出匹配的节日场景。
    
    返回格式为紧凑的文本格式，便于模型解析和筛选。

    Returns:
        所有节日数据的格式化字符串，格式为：
        节日数据列表（共XX条）：
        1 | ID:1 | 春节 | 节日营销
        2 | ID:2 | 情人节 | 节日营销
        ...
    """
    festivals = _get_cached_festivals()
    
    if not festivals:
        return "未找到节日数据，请检查数据库连接或数据表配置"

    result_parts = []
    result_parts.append(f"节日数据列表（共{len(festivals)}条）：")
    result_parts.append("")
    
    for i, record in enumerate(festivals, 1):
        festival_id = record.get('id', 'N/A')
        festival_name = record.get('festival_name', 'N/A')
        scene_type = record.get('scene_type', 'N/A')
        result_parts.append(f"{i} | ID:{festival_id} | {festival_name} | {scene_type}")
    
    result_parts.append("")
    result_parts.append("说明：请基于 get_festival_date_info() 返回的当前时间信息，以及用户的问题意图，从上述节日数据中筛选出匹配的节日场景。筛选结果必须包含 festival_name 和 scene_type 两个字段，且必须来自上述真实数据，禁止编造。")
    
    return "\n".join(result_parts)


__all__ = [
    "get_festivals_nearby",
    "get_festival_date_info",
    "get_all_festivals",
    "save_matched_festivals",
    "query_festival_by_name",
    "query_festivals_by_scene",
]
