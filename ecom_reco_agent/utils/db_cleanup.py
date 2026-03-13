"""
HITL 会话数据库清理工具
定期清理过期的会话数据，防止数据库文件过大
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from agno.utils.log import log_info, log_warning, log_error

logger = logging.getLogger(__name__)


def cleanup_expired_sessions(
    db_path: Path,
    session_table: str = "ecom_reco_sessions",
    days_to_keep: int = 30,
    dry_run: bool = False,
) -> int:
    """
    清理过期的 HITL 会话数据
    
    Args:
        db_path: 数据库文件路径
        session_table: 会话表名
        days_to_keep: 保留最近 N 天的数据，默认 30 天
        dry_run: 如果为 True，只统计不删除
        
    Returns:
        删除的记录数
    """
    if not db_path.exists():
        log_warning(f"数据库文件不存在: {db_path}")
        return 0
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (session_table,)
        )
        if not cursor.fetchone():
            log_warning(f"表 {session_table} 不存在")
            conn.close()
            return 0
        
        # 获取表结构，查找时间戳字段
        cursor.execute(f"PRAGMA table_info({session_table})")
        columns_info = cursor.fetchall()
        columns = {row[1]: row[2] for row in columns_info}
        
        # Agno 通常使用 updated_at 或 created_at 字段
        time_column = None
        for col in ["updated_at", "created_at", "timestamp", "last_updated"]:
            if col in columns:
                time_column = col
                break
        
        if not time_column:
            log_warning(f"表 {session_table} 中未找到时间戳字段（updated_at, created_at等）")
            conn.close()
            return 0
        
        # 计算过期时间点
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_timestamp = cutoff_date.timestamp()
        
        # 统计要删除的记录数
        # 假设时间戳字段存储的是 Unix 时间戳（秒）或 ISO 格式字符串
        # 先尝试 Unix 时间戳格式
        cursor.execute(
            f"SELECT COUNT(*) FROM {session_table} WHERE CAST({time_column} AS REAL) < ?",
            (cutoff_timestamp,)
        )
        count = cursor.fetchone()[0]
        
        if count == 0:
            log_info(f"没有需要清理的过期会话（保留 {days_to_keep} 天）")
            conn.close()
            return 0
        
        log_info(f"找到 {count} 条过期会话记录（超过 {days_to_keep} 天）")
        
        if dry_run:
            log_info("【DRY RUN】不会实际删除数据")
            conn.close()
            return count
        
        # 执行删除
        cursor.execute(
            f"DELETE FROM {session_table} WHERE CAST({time_column} AS REAL) < ?",
            (cutoff_timestamp,)
        )
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        # 执行 VACUUM 压缩数据库
        log_info("执行 VACUUM 压缩数据库...")
        cursor.execute("VACUUM")
        
        conn.close()
        
        # 获取清理后的文件大小
        new_size = db_path.stat().st_size / (1024 * 1024)  # MB
        log_info(
            f"✅ 清理完成：删除了 {deleted_count} 条记录，"
            f"数据库大小: {new_size:.2f} MB"
        )
        
        return deleted_count
        
    except sqlite3.Error as e:
        log_error(f"清理数据库时出错: {e}")
        raise
    except Exception as e:
        log_error(f"清理过程中发生未知错误: {e}")
        raise


def get_database_info(
    db_path: Path, 
    session_table: str = "ecom_reco_sessions"
) -> dict:
    """
    获取数据库信息
    
    Args:
        db_path: 数据库文件路径
        session_table: 会话表名
        
    Returns:
        包含数据库大小、记录数等信息的字典
    """
    info = {
        "exists": False,
        "size_mb": 0,
        "table_exists": False,
        "record_count": 0,
        "columns": [],
    }
    
    if not db_path.exists():
        return info
    
    info["exists"] = True
    info["size_mb"] = db_path.stat().st_size / (1024 * 1024)
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (session_table,)
        )
        if cursor.fetchone():
            info["table_exists"] = True
            
            # 获取记录数
            cursor.execute(f"SELECT COUNT(*) FROM {session_table}")
            info["record_count"] = cursor.fetchone()[0]
            
            # 获取列信息
            cursor.execute(f"PRAGMA table_info({session_table})")
            info["columns"] = [row[1] for row in cursor.fetchall()]
        
        conn.close()
    except sqlite3.Error as e:
        log_error(f"获取数据库信息时出错: {e}")
    
    return info


__all__ = [
    "cleanup_expired_sessions",
    "get_database_info",
]
