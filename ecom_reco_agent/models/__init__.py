"""
模型模块 - 提供统一的模型创建接口
"""

from .model_factory import create_model, load_llm_config

__all__ = [
    "create_model",
    "load_llm_config",
]
