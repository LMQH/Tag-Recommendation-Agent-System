"""
search_data 配置

说明：
- 不要把密钥写进代码文件（容易泄露/误提交）。
- 推荐：把 Qwen API Key 放在本机私密文件里，由本配置读取；或使用环境变量。
"""

import os
from pathlib import Path
from typing import Optional


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def read_text_file(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.exists() or not p.is_file():
        return None
    text = p.read_text(encoding="utf-8").strip()
    return text or None


# ===== Qwen / DashScope(OpenAI compatible) =====
QWEN_BASE_URL = env("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
# Qwen API Key：
# 说明：你要求“直接写在 config.py 里”，这里提供内联 key 的配置位（风险：容易泄露/误提交，请自行确保不提交到代码仓库）。
# 优先级：环境变量 DASHSCOPE_API_KEY > 本文件内联 DASHSCOPE_API_KEY_INLINE > 本机私密文件（默认 ~/.config/yzh/dashscope_api_key）
#
# 用法：
# 1) 把你的 key 粘到下面这个变量里（只在你本机使用，不要提交）
# 2) 重新运行建库脚本即可
DASHSCOPE_API_KEY_INLINE = "sk-f999bd21ac0641c2a4f4e28ee6b0df6e"  # TODO: paste your DashScope API key here, e.g. "sk-xxxx"
DASHSCOPE_API_KEY_FILE = env("DASHSCOPE_API_KEY_FILE", "~/.config/yzh/dashscope_api_key")
QWEN_API_KEY = env("DASHSCOPE_API_KEY") or (DASHSCOPE_API_KEY_INLINE.strip() or None) or read_text_file(DASHSCOPE_API_KEY_FILE)

# embedding
QWEN_EMBEDDING_MODEL = env("QWEN_EMBEDDING_MODEL", "text-embedding-v4")

# rerank（推荐使用 OpenAI 兼容 rerank 端点：/compatible-api/v1/reranks）
QWEN_RERANK_BASE_URL = env("QWEN_RERANK_BASE_URL", "https://dashscope.aliyuncs.com")
QWEN_RERANK_PATH = env("QWEN_RERANK_PATH", "/compatible-api/v1/reranks")
QWEN_RERANK_MODEL = env("QWEN_RERANK_MODEL", "qwen3-rerank")
# 可选：rerank instruct（OpenAI 兼容 rerank 端点支持）
# 优先级：环境变量 > instruct 文件 > 默认值
QWEN_RERANK_INSTRUCT_FILE = env(
    "QWEN_RERANK_INSTRUCT_FILE",
    str(Path(__file__).with_name("rerank_instruct_brand.txt")),
)
_DEFAULT_RERANK_INSTRUCT = (
    "Given a brand-name query, rank candidate brand names by whether they refer to the same brand. "
    "Prefer exact match and standard spelling. Do NOT rank by general topical similarity."
)
QWEN_RERANK_INSTRUCT = env("QWEN_RERANK_INSTRUCT") or read_text_file(QWEN_RERANK_INSTRUCT_FILE) or _DEFAULT_RERANK_INSTRUCT

# 品类 rerank instruct（与品牌提示词分开，避免混用）
QWEN_RERANK_INSTRUCT_CATEGORY_FILE = env(
    "QWEN_RERANK_INSTRUCT_CATEGORY_FILE",
    str(Path(__file__).with_name("rerank_instruct_category.txt")),
)
_DEFAULT_RERANK_INSTRUCT_CATEGORY = (
    "Given a category query, rank candidate categories by whether the candidate is the best category node for this query. "
    "Use the structured fields (CODE/NAME/L1/L2/L3/LEVEL). Do NOT rank by general topical similarity."
)
QWEN_RERANK_INSTRUCT_CATEGORY = (
    env("QWEN_RERANK_INSTRUCT_CATEGORY")
    or read_text_file(QWEN_RERANK_INSTRUCT_CATEGORY_FILE)
    or _DEFAULT_RERANK_INSTRUCT_CATEGORY
)


# ===== Milvus =====
MILVUS_HOST = env("MILVUS_HOST", "121.37.229.249")
MILVUS_PORT = int(env("MILVUS_PORT", "19530") or "19530")
MILVUS_DB_NAME = env("MILVUS_DB_NAME", "default")
# Milvus collection 名称限制：只能包含字母/数字/下划线，不能用中文
# 你想要的逻辑命名是：“AI_过滤” + “云台品牌”
# 这里用合法的物理命名：AI_filter_yuntai_brand
MILVUS_COLLECTION_BRAND = env("MILVUS_COLLECTION_BRAND", "AI_filter_yuntai_brand")
# 品类 collection（物理名）
MILVUS_COLLECTION_CATEGORY = env("MILVUS_COLLECTION_CATEGORY", "AI_filter_yuntai_category")


# ===== MySQL 品牌表 =====
MYSQL_BRAND_TABLE = env("MYSQL_BRAND_TABLE", "skycrane_goods.t_brand")
MYSQL_BRAND_ID_COL = env("MYSQL_BRAND_ID_COL", "id")
MYSQL_BRAND_NAME_COL = env("MYSQL_BRAND_NAME_COL", "brand_name")  # 如果你们有规范化列，可通过 env 覆盖
# 方案1：Milvus 内保留全量数据；是否展示由检索时的 Milvus expr 决定
# 因此建库默认不过滤 is_deleted/is_enabled（可通过 env 覆盖）
MYSQL_BRAND_FILTER = env("MYSQL_BRAND_FILTER", "1=1")

# ===== MySQL 品类表 =====
MYSQL_CATEGORY_TABLE = env("MYSQL_CATEGORY_TABLE", "skycrane_goods.t_base_category")
MYSQL_CATEGORY_ID_COL = env("MYSQL_CATEGORY_ID_COL", "id")
MYSQL_CATEGORY_CODE_COL = env("MYSQL_CATEGORY_CODE_COL", "category_code")
MYSQL_CATEGORY_NAME_COL = env("MYSQL_CATEGORY_NAME_COL", "category_name")
MYSQL_CATEGORY_PARENT_CODE_COL = env("MYSQL_CATEGORY_PARENT_CODE_COL", "parent_code")
MYSQL_CATEGORY_LEVEL_COL = env("MYSQL_CATEGORY_LEVEL_COL", "category_level")
MYSQL_CATEGORY_FILTER = env("MYSQL_CATEGORY_FILTER", "1=1")
