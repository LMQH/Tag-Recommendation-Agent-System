"""
模型工厂模块 - 根据配置自动创建合适的模型实例
"""

from typing import Any, Dict, Optional

from agno.models.dashscope import DashScope
from agno.models.openai import OpenAIChat
from agno.models.deepseek import DeepSeek


def load_llm_config() -> Dict[str, Any]:
    """
    加载 LLM 配置
    
    Returns:
        LLM 配置字典
    """
    from config.config_loader import get_llm_config
    llm = get_llm_config()  # 自动根据域名/IP识别环境
    # 确保类型转换（保持与旧版本一致）
    llm["temperature"] = float(llm.get("temperature", 0.2))
    llm["max_retries"] = int(llm.get("max_retries", 0) or 0)
    return llm


def create_model(llm_config: Optional[Dict[str, Any]] = None):
    """
    根据配置自动创建合适的模型实例
    
    支持三种模型类型：
    1. deepseek - 使用 DeepSeek 类（适用于 deepseek 私有部署，解决 developer 角色兼容性问题）
    2. dashscope - 使用 DashScope 类（适用于 Qwen/DashScope）
    3. openai - 使用 OpenAIChat 类（适用于其他 OpenAI 兼容 API）
    
    模型选择逻辑：
    - 优先使用 model_type 显式指定
    - 如果没有指定，根据 base_url 和 model_name 自动判断：
      - 包含 "modelarts-maas" 或 "deepseek" -> DeepSeek
      - 包含 "dashscope" -> DashScope (Qwen)
      - 其他 -> OpenAIChat (OpenAI 兼容)
    
    Args:
        llm_config: LLM 配置字典，如果为 None 则自动加载配置
        
    Returns:
        模型实例
        
    Raises:
        ValueError: 如果未配置 API Key
    """
    if llm_config is None:
        llm_config = load_llm_config()
    
    api_key = (llm_config.get("api_key") or "").strip()
    if not api_key:
        raise ValueError("未配置 API Key，请在 config/dev.json 的 llm.api_key 填写 key")
    
    model_type = llm_config.get("model_type", "").lower()
    base_url = llm_config.get("base_url", "").lower()
    model_name = llm_config.get("model_name", "").lower()
    
    # 判断使用哪个模型类
    if model_type == "deepseek" or (not model_type and ("modelarts-maas" in base_url or "deepseek" in base_url or "deepseek" in model_name)):
        # 使用 DeepSeek 模型类（适用于 deepseek 私有部署，解决 developer 角色兼容性问题）
        model = DeepSeek(
            id=llm_config["model_name"],
            api_key=api_key,
            base_url=llm_config["base_url"],
            temperature=llm_config.get("temperature", 0.2),
        )
    elif model_type == "dashscope" or (not model_type and "dashscope" in base_url):
        # 使用 DashScope 模型类（适用于 Qwen/DashScope）
        model = DashScope(
            id=llm_config["model_name"],
            api_key=api_key,
            base_url=llm_config["base_url"],
            temperature=llm_config.get("temperature", 0.2),
        )
    else:
        # 使用 OpenAI 兼容的模型类（适用于其他 OpenAI 兼容 API）
        model = OpenAIChat(
            id=llm_config["model_name"],
            api_key=api_key,
            base_url=llm_config["base_url"],
            temperature=llm_config.get("temperature", 0.2),
        )
    
    return model
