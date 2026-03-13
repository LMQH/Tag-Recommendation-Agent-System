"""
Agno 日志配置模块 - 基于 Agno 框架的日志系统

功能：
- 文件日志：记录所有级别的 agno 日志到文件（按大小轮转）
- 控制台日志：始终只输出INFO级别及以上（INFO/WARNING/ERROR），不输出DEBUG
- 使用 Agno 框架的自动识别机制：配置名为 "agno" 的日志器，Agent 会自动识别并使用

参考实现：
```python
logger = logging.getLogger("agno")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("agent_debug.log")
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.propagate = False
# Agno 会自动使用这个 logger
agent = Agent(debug_mode=True, debug_level=2)
```

日志级别策略：
- 文件日志：记录所有级别（DEBUG及以上）
- 控制台输出：只输出INFO级别及以上（INFO/WARNING/ERROR）
- Agent参数：debug_mode 和 debug_level 主要用于控制 Agent 内部行为
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# 获取项目根目录（ecom_reco_agent的父目录）
_CURRENT_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _CURRENT_FILE.parents[1]  # ecom_reco_agent/utils/agno_logger.py -> ecom_reco_agent -> 项目根目录


def setup_agno_logging(
    log_level: int = 1,
    debug_level: str = "INFO",
    log_dir: str = "log",
    log_file: str = "app.log",
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    设置 Agno 日志系统（使用 Agno 自动识别机制）
    
    通过配置名为 "agno" 的日志器并设置 logger.propagate = False，
    Agent 会自动识别并使用该日志器。

    Args:
        log_level: 调试级别（1或2，默认1）。用于 Agent 的 debug_level 参数：
            - 1: 只显示普通调试日志（log_debug(..., log_level=1)）
            - 2: 显示所有调试日志（包括 log_debug(..., log_level=2)）
            注意：此参数不影响文件日志，文件日志始终记录所有级别
        debug_level: 日志级别（DEBUG/INFO/WARNING/ERROR，默认INFO）
            用于确定 Agent 的 debug_mode 参数：
            - DEBUG: Agent debug_mode=True
            - 其他: Agent debug_mode=False
        log_dir: 日志目录（相对于项目根目录）
        log_file: 日志文件名
        max_bytes: 单个日志文件最大字节数（默认10MB）
        backup_count: 保留的备份文件数量（默认5个）
    """
    # 创建日志目录
    log_dir_path = _PROJECT_ROOT / log_dir
    log_dir_path.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir_path / log_file

    # 获取名为 "agno" 的日志器（Agno 会自动识别）
    logger = logging.getLogger("agno")
    logger.setLevel(logging.DEBUG)  # 设置为最低级别，确保所有日志都能被创建

    # 清除现有的处理器（避免重复添加）
    logger.handlers.clear()

    # 日志格式
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)

    # 文件处理器：记录所有级别（DEBUG及以上）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
    
    # 添加自定义过滤器，确保所有 DEBUG 级别的日志都能写入文件
    # 同时截断过长的提示词内容
    class FileDebugFilter(logging.Filter):
        """文件日志过滤器：确保所有 DEBUG 及以上级别的日志都能写入文件，并截断过长的提示词"""
        # 提示词相关关键词，用于识别提示词日志
        INSTRUCTIONS_KEYWORDS = [
            "<your_role>",
            "your_role",
            "instructions",
            "系统提示",
            "工作流程",
            "可用工具",
            "最终输出",
            "候选推荐列表",
            "流程要求",
            "==================================================================== system",
        ]
        # 最大消息长度（字符数），超过此长度将截断
        MAX_MESSAGE_LENGTH = 500
        
        def filter(self, record):
            # 允许所有 DEBUG 及以上级别的日志
            if record.levelno < logging.DEBUG:
                return False
            
            # 获取消息内容
            message = record.getMessage()
            
            # 检查是否是提示词相关的日志（包含关键词或消息过长）
            is_instructions_log = any(
                keyword in message for keyword in self.INSTRUCTIONS_KEYWORDS
            ) or len(message) > 1000  # 如果消息超过1000字符，也认为是提示词日志
            
            # 如果是提示词日志且消息过长，进行截断
            if is_instructions_log and len(message) > self.MAX_MESSAGE_LENGTH:
                # 截断消息，保留前部分并添加截断提示
                # 尝试在换行符处截断，避免截断到中间
                truncated = message[:self.MAX_MESSAGE_LENGTH]
                last_newline = truncated.rfind('\n')
                if last_newline > self.MAX_MESSAGE_LENGTH * 0.8:  # 如果最后换行符位置合理，在换行符处截断
                    truncated = truncated[:last_newline]
                
                truncated_message = truncated + f"\n... [提示词内容已截断，原始长度: {len(message)} 字符]"
                record.msg = truncated_message
                record.args = ()  # 清空 args，因为我们已经修改了 msg
            
            return True
    
    file_handler.addFilter(FileDebugFilter())
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台处理器：只输出INFO级别及以上
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # 只输出INFO及以上，不输出DEBUG
    
    # 控制台格式（简化版，便于阅读）
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        date_format
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 关键：设置 propagate = False，避免日志传播到根日志器
    # 这样 Agno 会自动识别并使用这个日志器
    logger.propagate = False

    # 为常见的第三方库日志器设置更高的级别，避免记录它们的日志
    # 只记录 ERROR 及以上级别的日志（如果有的话）
    third_party_loggers = [
        "httpx",
        "httpcore",
        "httpcore.http11",
        "httpcore.http2",
        "httpcore.connection",
        "hpack",
        "hpack.hpack",
        "hpack.table",
        "openai",
        "openai._base_client",
        "urllib3",
        "urllib3.connectionpool",
        "requests",
        "requests.packages.urllib3",
        "numexpr",
    ]
    for logger_name in third_party_loggers:
        third_party_logger = logging.getLogger(logger_name)
        # 设置较高的级别，只记录 ERROR 及以上
        third_party_logger.setLevel(logging.ERROR)
        # 禁用传播，避免传播到根日志器
        third_party_logger.propagate = False

    # 对于所有以这些前缀开头的日志器，也设置较高的级别
    # 这样可以捕获所有子模块的日志
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        # 检查是否是第三方库的日志器
        if any(logger_name.startswith(prefix) for prefix in ["httpx", "httpcore", "hpack", "openai", "urllib3", "requests", "numexpr"]):
            if not logger_name.startswith("agno"):  # 确保不是 agno 相关的日志器
                third_party_logger = logging.getLogger(logger_name)
                third_party_logger.setLevel(logging.ERROR)
                third_party_logger.propagate = False


def setup_agno_logging_from_config(config: Optional[Dict[str, Any]] = None) -> None:
    """
    从配置字典设置 Agno 日志系统

    Args:
        config: 日志配置字典，如果为None则使用默认配置
    """
    if config is None:
        config = {}

    # 确保类型正确并验证 log_level 必须是 1 或 2
    log_level = config.get("log_level", 1)
    if not isinstance(log_level, int):
        try:
            log_level = int(log_level)
        except (ValueError, TypeError):
            log_level = 1
    
    # 验证 log_level 必须是 1 或 2
    if log_level not in (1, 2):
        log_level = 1  # 默认使用 1
    
    debug_level = config.get("debug_level", "INFO")
    if not isinstance(debug_level, str):
        debug_level = str(debug_level)

    setup_agno_logging(
        log_level=log_level,
        debug_level=debug_level,
        log_dir=config.get("log_dir", "log"),
        log_file=config.get("log_file", "app.log"),
        max_bytes=config.get("max_bytes", 10485760),
        backup_count=config.get("backup_count", 5),
    )


__all__ = ["setup_agno_logging", "setup_agno_logging_from_config"]
