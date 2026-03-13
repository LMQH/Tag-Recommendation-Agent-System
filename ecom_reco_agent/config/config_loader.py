"""
配置加载器 - 支持多环境配置

支持三种环境：
- dev: 开发环境（默认）
- show: 演示环境
- prod: 生产环境

通过域名自动识别环境
"""

from __future__ import annotations

import json
import os
import platform
import socket
from pathlib import Path
from typing import Any, Dict, Optional

from agno.utils.log import log_info, log_debug, log_warning, log_error


class ConfigLoader:
    """配置加载器，支持多环境配置"""

    def __init__(self, config_dir: Optional[str | Path] = None) -> None:
        """
        Args:
            config_dir: 配置文件目录，默认为 ecom_reco_agent/config/
        """
        if config_dir is None:
            # 默认配置目录
            current_file = Path(__file__)
            config_dir = current_file.parent
        else:
            config_dir = Path(config_dir)

        self.config_dir = config_dir
        self.domains_file = config_dir / "domains.json"
        self.dev_file = config_dir / "dev.json"  # 基础配置文件（原config.json）
        self.show_file = config_dir / "show.json"
        self.prod_file = config_dir / "prod.json"

        self._cache: Dict[str, Any] = {}
        self._cached_environment: Optional[str] = None  # 缓存环境识别结果，避免重复识别

    def _get_local_ip(self) -> str:
        """
        获取本机IP地址
        跨平台获取本地 IP 地址：
        - Linux: 优先尝试 eth0（云服务器内网 IP），失败则回退到 socket.connect
        - Windows/macOS: 使用 socket.connect 获取默认出口 IP
        """
        system = platform.system().lower()
        
        if system == "linux":
            # 优先尝试直接读取 eth0（适用于云服务器内网IP）
            try:
                import fcntl
                import struct
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                ip = socket.inet_ntoa(fcntl.ioctl(
                    s.fileno(),
                    0x8915,  # SIOCGIFADDR，用于"获取接口地址"
                    struct.pack('256s', b'eth0')
                )[20:24])
                s.close()
                log_debug(f"[Linux] 通过 eth0 获取内网 IP: {ip}", log_level=2)
                return ip
            except Exception as e:
                log_debug(f"读取 eth0 失败，回退到通用方法: {e}", log_level=2)
        
        # 通用方法：适用于 Windows / macOS / Linux 回退
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 连接到公网地址（不会发送数据）
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            log_debug(f"[{system}] 通过 socket.connect 获取 IP: {ip}", log_level=2)
            return ip
        except Exception as e:
            log_warning(f"获取本地 IP 失败: {e}")
            try:
                # 备用方法：获取localhost的IP
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    def get_environment(self, domain: Optional[str] = None) -> str:
        """
        根据域名/IP自动识别环境

        识别顺序：
        1. 如果提供了domain参数，直接使用（不缓存，因为domain可能不同）
        2. 如果设置了DOMAIN环境变量，使用环境变量
        3. 自动获取IP地址，与domains.json匹配
        4. 默认使用dev环境

        注意：如果domain为None，会缓存识别结果，避免重复识别和日志输出。

        Args:
            domain: 域名，如果为None则自动检测（会使用缓存结果）

        Returns:
            环境名称: dev, show, prod
        """
        # 如果提供了 domain 参数，需要重新识别（不缓存，因为 domain 可能不同）
        if domain is not None:
            return self._identify_environment(domain)
        
        # 如果已经缓存了环境，直接返回（不输出日志）
        if self._cached_environment is not None:
            return self._cached_environment
        
        # 第一次识别，输出日志并缓存结果
        environment = self._identify_environment(None)
        self._cached_environment = environment
        return environment
    
    def _identify_environment(self, domain: Optional[str] = None) -> str:
        """
        实际的环境识别逻辑
        
        Args:
            domain: 域名，如果为None则自动检测
            
        Returns:
            环境名称: dev, show, prod
        """
        # 加载域名配置
        if not self.domains_file.exists():
            log_warning(f"域名配置文件不存在: {self.domains_file}")
            return "dev"

        try:
            with open(self.domains_file, encoding="utf-8") as f:
                domains_config = json.load(f)
        except Exception as e:
            log_warning(f"加载域名配置失败: {e}")
            return "dev"

        # 收集所有可能的标识符用于匹配
        identifiers_to_check = []

        # 1. 如果提供了domain参数，优先使用
        if domain:
            identifiers_to_check.append(domain)
        # 2. 如果设置了DOMAIN环境变量，使用环境变量
        elif os.getenv("DOMAIN"):
            identifiers_to_check.append(os.getenv("DOMAIN"))
        else:
            # 3. 自动获取IP地址
            local_ip = self._get_local_ip()
            if local_ip:
                identifiers_to_check.append(local_ip)
                log_debug(f"自动获取IP地址: {local_ip}", log_level=2)  # 重复性日志，使用2级

        # 如果没有找到任何标识符，使用默认环境
        if not identifiers_to_check:
            log_info("未找到域名/IP标识，使用默认 dev 环境")
            return "dev"

        # 检查每个标识符是否匹配环境配置
        for identifier in identifiers_to_check:
            identifier_lower = identifier.lower().strip()

            # 检查是否在prod域名列表中
            prod_domains = domains_config.get("environments", {}).get("prod", {}).get("domains", [])
            prod_domains_lower = [d.lower().strip() for d in prod_domains]
            if identifier_lower in prod_domains_lower:
                log_info(f"根据标识符 '{identifier}' 识别为 prod 环境")
                return "prod"

            # 检查是否在show域名列表中
            show_domains = domains_config.get("environments", {}).get("show", {}).get("domains", [])
            show_domains_lower = [d.lower().strip() for d in show_domains]
            if identifier_lower in show_domains_lower:
                log_info(f"根据标识符 '{identifier}' 识别为 show 环境")
                return "show"

            # 检查是否在dev域名列表中（虽然默认就是dev，但可以显式匹配）
            dev_domains = domains_config.get("environments", {}).get("dev", {}).get("domains", [])
            dev_domains_lower = [d.lower().strip() for d in dev_domains]
            if identifier_lower in dev_domains_lower:
                log_info(f"根据标识符 '{identifier}' 识别为 dev 环境")
                return "dev"

        # 如果没有匹配到任何环境，使用默认dev环境
        log_info(f"标识符 {identifiers_to_check} 未匹配到任何环境配置，使用默认 dev 环境")
        return "dev"

    def load_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置

        配置优先级：
        - dev环境：直接使用dev.json
        - show/prod环境：dev.json + 环境文件（环境文件覆盖dev.json）

        Args:
            environment: 环境名称，如果为None则自动识别

        Returns:
            配置字典
        """
        if environment is None:
            environment = self.get_environment()


        # dev环境：直接使用dev.json
        if environment == "dev":
            dev_config = self._load_json_file(self.dev_file)
            if dev_config is None:
                raise ValueError(f"开发环境配置文件不存在: {self.dev_file}")
            self._cache[environment] = dev_config
            return dev_config

        # show和prod环境：dev.json + 环境文件（覆盖）
        base_config = self._load_json_file(self.dev_file)
        if base_config is None:
            log_warning(f"基础配置文件不存在: {self.dev_file}，将使用空配置")
            base_config = {}
        
        # 安全获取环境文件路径
        env_file_attr = f"{environment}_file"
        if not hasattr(self, env_file_attr):
            raise ValueError(f"不支持的环境: {environment}，支持的环境: dev, show, prod")
        env_file = getattr(self, env_file_attr)
        
        env_config = self._load_json_file(env_file)
        if env_config is None:
            log_warning(f"环境配置文件不存在: {env_file}，将仅使用基础配置")
            env_config = {}

        # 合并配置（环境配置覆盖基础配置）
        config = self._deep_merge(base_config, env_config)

        self._cache[environment] = config
        return config

    def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载JSON文件"""
        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            log_error(f"加载配置文件失败: {file_path}, error: {e}")
            return None

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_llm_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """获取LLM配置"""
        config = self.load_config(environment)
        return config.get("llm", {})


    def get_api_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取API配置（真实数据接口配置）

        Args:
            environment: 环境名称，如果为None则自动识别

        Returns:
            API配置字典，包含：
            - base_url: API基础地址
            - timeout: HTTP请求超时时间（秒）
            - max_results: 最大返回结果数量
            - max_retries: 最大重试次数
            - retry_delay: 重试延迟时间（秒）
        """
        config = self.load_config(environment)
        return config.get("api", {
            "base_url": "https://api-show.haoxiny.com/open/api/aiTrim",
            "timeout": 8.0,
            "max_results": 50,
            "max_retries": 0,
            "retry_delay": 1.0
        })

    def get_agentos_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """获取AgentOS配置"""
        config = self.load_config(environment)
        return config.get("agentos", {"port": 14466, "host": "0.0.0.0"})

    def get_search_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取搜索配置（Milvus + Qwen）

        Args:
            environment: 环境名称，如果为None则自动识别

        Returns:
            搜索配置字典，包含：
            - milvus: Milvus 连接配置
            - qwen: Qwen API 配置
            - default_params: 默认参数
        """
        config = self.load_config(environment)
        return config.get("search", {
            "milvus": {
                "host": "121.37.229.249",
                "port": 19530,
                "db_name": "default"
            },
            "qwen": {
                "api_key": "sk-f999bd21ac0641c2a4f4e28ee6b0df6e",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
            },
            "default_params": {
                "enable_rerank": True,
                "timeout": 30
            }
        })

    def get_agent_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取Agent配置

        Args:
            environment: 环境名称，如果为None则自动识别

        Returns:
            Agent配置字典，包含：
            - num_history_runs: 对话历史轮次
            - max_tool_calls_from_history: 从历史加载的工具调用数量
            - prompt_mode: Prompt 装配模式，支持 legacy 或 layered
            - max_query_retry_count: 查询阶段允许的最大回退次数
            - debug_mode: 是否启用调试模式
            - stream: 是否启用流式输出
            - stream_events: 是否启用事件流
            - enable_agentic_memory: 是否启用长期记忆
            - add_history_to_context: 是否将历史添加到上下文
            - markdown: 是否使用Markdown格式
            - hitl_session_retention_days: HITL会话保留天数，默认30天，超过此天数的会话将在启动时自动清理
        """
        config = self.load_config(environment)
        return config.get("agent", {
            "num_history_runs": 10,
            "max_tool_calls_from_history": 0,
            "prompt_mode": "layered",
            "max_query_retry_count": 2,
            "debug_mode": True,
            "stream": True,
            "stream_events": True,
            "enable_agentic_memory": True,
            "add_history_to_context": True,
            "markdown": True
        })

    def get_reasoning_tools_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取推理工具配置

        Args:
            environment: 环境名称，如果为None则自动识别

        Returns:
            推理工具配置字典，包含：
            - add_instructions: 是否添加指令
            - add_few_shot: 是否添加few-shot示例
            - enable_think: 是否启用think工具
            - enable_analyze: 是否启用analyze工具
        """
        config = self.load_config(environment)
        return config.get("reasoning_tools", {
            "add_instructions": True,
            "add_few_shot": False,
            "enable_think": True,
            "enable_analyze": True
        })

    def get_query_normalization_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取查询标准化工具配置

        Args:
            environment: 环境名称，如果为None则自动识别

        Returns:
            查询标准化工具配置字典，包含：
            - top_k: 向量召回数量（默认100）
            - top_n: 最终返回数量（默认12）
            - enable_rerank: 是否启用Rerank精排（默认True）
            - timeout: 超时时间（秒，默认30）
            - vector_score_threshold: 向量分数阈值（默认0.85）
            - min_high_score_count: 最少高分结果数量（默认3）
            - use_smart_rerank: 是否启用智能rerank策略（默认True）
        """
        config = self.load_config(environment)
        return config.get("query_normalization", {
            "top_k": 100,  # 更新默认值
            "top_n": 12,
            "enable_rerank": True,
            "timeout": 30,
            "vector_score_threshold": 0.85,  # 新增默认值
            "min_high_score_count": 3,       # 新增默认值
            "use_smart_rerank": True         # 新增默认值
        })

    def get_festival_tools_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取节日工具配置

        Args:
            environment: 环境名称，如果为None则自动识别

        Returns:
            节日工具配置字典，包含：
            - days_ahead: 查询未来多少天的节日（默认30天）
            - cache_refresh_interval_hours: 缓存刷新间隔（小时，默认24小时）
        """
        config = self.load_config(environment)
        return config.get("festival_tools", {
            "days_ahead": 30,
            "cache_refresh_interval_hours": 24
        })

    def get_recommendation_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取推荐数据传输配置

        Args:
            environment: 环境名称，如果为None则自动识别

        Returns:
            推荐数据传输配置字典，包含：
            - transfer_url: 数据传输接口地址（根据 host 和 port 自动拼接，路径固定为 /recommendations/data）
            - host: 接口主机地址（可选，默认使用 agentos.host）
            - port: 接口端口（可选，默认使用 agentos.port）
            - timeout: HTTP 请求超时时间（秒）
            - max_retries: 最大重试次数
            - retry_delay: 重试延迟时间（秒）
        """
        config = self.load_config(environment)
        agentos_config = self.get_agentos_config(environment)
        
        # 获取推荐数据传输配置，如果没有则使用 agentos 的配置
        recommendation_config = config.get("recommendation", {})
        host = recommendation_config.get("host") or agentos_config.get("host", "0.0.0.0")
        port = recommendation_config.get("port") or agentos_config.get("port", 14466)
        
        # 路径固定为 /recommendations/data，不支持修改
        # 如果 host 是 0.0.0.0，则使用 localhost 访问
        if host == "0.0.0.0":
            access_host = "localhost"
        else:
            access_host = host
        
        transfer_url = f"http://{access_host}:{port}/recommendations/data"
        
        return {
            "transfer_url": transfer_url,
            "host": host,
            "port": port,
            "timeout": recommendation_config.get("timeout", 10.0),
            "max_retries": recommendation_config.get("max_retries", 2),
            "retry_delay": recommendation_config.get("retry_delay", 1.0)
        }

    def get_logging_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        获取日志配置

        Args:
            environment: 环境名称，如果为None则自动识别

        Returns:
            日志配置字典，包含：
            - log_level: 调试级别（1或2，默认1）。当 debug_level=DEBUG 时生效
            - debug_level: 控制台日志级别（DEBUG/INFO/WARNING/ERROR，默认INFO）
            - log_dir: 日志目录（默认log）
            - log_file: 日志文件名（默认app.log）
            - max_bytes: 单个日志文件最大字节数（默认10485760，10MB）
            - backup_count: 保留的备份文件数量（默认5）
        """
        config = self.load_config(environment)
        return config.get("logging", {
            "log_level": 1,
            "debug_level": "INFO",
            "log_dir": "log",
            "log_file": "app.log",
            "max_bytes": 10485760,
            "backup_count": 5
        })


# 全局配置加载器实例
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_dir: Optional[str | Path] = None) -> ConfigLoader:
    """获取配置加载器实例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
    return _config_loader


def load_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：加载配置"""
    return get_config_loader().load_config(environment)


def get_llm_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取LLM配置"""
    return get_config_loader().get_llm_config(environment)


def get_api_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取API配置"""
    return get_config_loader().get_api_config(environment)


def get_agentos_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取AgentOS配置"""
    return get_config_loader().get_agentos_config(environment)


def get_search_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取搜索配置（Milvus + Qwen）"""
    return get_config_loader().get_search_config(environment)


def get_agent_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取Agent配置"""
    return get_config_loader().get_agent_config(environment)


def get_reasoning_tools_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取推理工具配置"""
    return get_config_loader().get_reasoning_tools_config(environment)


def get_query_normalization_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取查询标准化工具配置"""
    return get_config_loader().get_query_normalization_config(environment)


def get_festival_tools_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取节日工具配置"""
    return get_config_loader().get_festival_tools_config(environment)


def get_recommendation_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取推荐数据传输配置"""
    return get_config_loader().get_recommendation_config(environment)


def get_logging_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取日志配置"""
    return get_config_loader().get_logging_config(environment)


__all__ = [
    "ConfigLoader",
    "get_config_loader",
    "load_config",
    "get_llm_config",
    "get_api_config",
    "get_agentos_config",
    "get_search_config",
    "get_agent_config",
    "get_reasoning_tools_config",
    "get_query_normalization_config",
    "get_festival_tools_config",
    "get_recommendation_config",
    "get_logging_config",
]
