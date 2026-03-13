# 配置文件说明

本目录包含多环境配置文件，支持开发、演示和生产三种环境。

## 配置文件结构

```
config/
├── dev.json         # 开发环境配置
├── show.json        # 演示环境配置
├── prod.json        # 生产环境配置
├── domains.json     # 域名环境映射配置
├── config_loader.py # 配置加载器
└── README.md        # 配置文件说明文档
```

## 配置说明

每个环境使用独立的配置文件（`dev.json`、`show.json`、`prod.json`），配置项完全独立，不存在基础配置覆盖机制。系统根据当前环境自动加载对应的配置文件。

## 环境识别

系统会自动识别环境，识别顺序如下：

1. **显式指定域名**
   - 在代码中调用 `get_environment(domain="example.com")` 显式指定

2. **环境变量指定**
   - 设置环境变量 `DOMAIN=your-domain.com`
   - 系统会根据 `domains.json` 中的配置自动识别环境

3. **自动获取IP地址**（推荐）
   - 系统会自动获取当前机器的IP地址
   - 与 `domains.json` 中的配置进行匹配
   - 如果匹配到某个环境的域名列表，就使用该环境配置
   - **无需手动设置，系统会自动识别**

4. **手动指定环境**
   - 在代码中调用 `load_config(environment="prod")` 手动指定

5. **默认环境**
   - 如果都不匹配，默认使用 `dev` 环境

**配置示例（domains.json）：**
```json
{
  "environments": {
    "prod": {
      "domains": [
        "192.168.1.100",            // IP地址
        "example.com"               // 域名
      ]
    },
    "show": {
      "domains": [
        "192.168.1.200"             // IP地址
      ]
    },
    "dev": {
      "domains": [
        "localhost",
        "127.0.0.1"                 // IP地址
      ]
    }
  }
}
```

**工作原理：**
- 系统启动时会自动获取当前机器的IP地址
- 将IP地址与 `domains.json` 中的配置进行匹配（不区分大小写）
- 如果匹配到某个环境的域名列表，就使用该环境配置
- 如果都不匹配，默认使用 `dev` 环境

## 使用方法

### 1. 基础使用

```python
from config.config_loader import get_llm_config, load_config

# 自动识别环境并加载配置
llm_config = get_llm_config()
print(f"使用模型: {llm_config['model_name']}")

# 加载完整配置
config = load_config()
print(f"API地址: {config['api']['base_url']}")
```

### 2. 手动指定环境

```python
from config.config_loader import load_config

# 强制使用生产环境配置
prod_config = load_config(environment="prod")

# 强制使用开发环境配置
dev_config = load_config(environment="dev")
```

## 配置项说明

### LLM 配置 (`llm`)

```json
{
  "llm": {
    "base_url": "API基础URL",
    "api_key": "API密钥",
    "model_name": "模型名称（如 qwen-plus, qwen-max）",
    "model_type": "dashscope",
    "temperature": 0.2,
    "timeout": 120,
    "max_retries": 3
  }
}
```

**字段说明**：
- `base_url`: LLM API 的基础URL
- `api_key`: API密钥
- `model_name`: 模型名称，如 `qwen-plus`、`qwen-max` 等
- `model_type`: 模型类型，如 `dashscope`
- `temperature`: 温度参数，控制输出的随机性（0-1）
- `timeout`: 请求超时时间（秒）
- `max_retries`: 最大重试次数

### Agent 配置 (`agent`)

```json
{
  "agent": {
    "num_history_runs": 10,
    "max_tool_calls_from_history": 0,
    "debug_mode": false,
    "stream": true,
    "stream_events": true,
    "enable_agentic_memory": true,
    "add_history_to_context": true,
    "markdown": true
  }
}
```

**字段说明**：
- `num_history_runs`: 保留的历史运行次数
- `max_tool_calls_from_history`: 从历史中获取的最大工具调用数
- `debug_mode`: 是否启用调试模式
- `stream`: 是否启用流式输出
- `stream_events`: 是否启用事件流
- `enable_agentic_memory`: 是否启用智能记忆
- `add_history_to_context`: 是否将历史添加到上下文
- `markdown`: 是否启用 Markdown 格式输出
- `hitl_session_retention_days`: HITL会话保留天数，超过此天数的会话将在启动时自动清理（默认30天）

### API 配置 (`api`)

```json
{
  "api": {
    "base_url": "外部API地址",
    "timeout": 8.0,
    "max_results": 50,
    "max_retries": 0,
    "retry_delay": 1.0
  }
}
```

**字段说明**：
- `base_url`: 外部API的基础URL
- `timeout`: 请求超时时间（秒）
- `max_results`: 最大返回结果数
- `max_retries`: 最大重试次数
- `retry_delay`: 重试延迟时间（秒）

### AgentOS 配置 (`agentos`)

```json
{
  "agentos": {
    "port": 14466,
    "host": "0.0.0.0",
    "reload": false,
    "workers": 4,
    "log_level": "INFO",
    "access_log_console": false
  }
}
```

**字段说明**：
- `port`: 服务端口号（默认14466）
- `host`: 服务主机地址（默认"0.0.0.0"）
- `reload`: 是否启用自动重载（开发环境建议true，生产环境false）
- `workers`: 工作进程数（生产环境建议设置为CPU核心数）
- `log_level`: AgentOS 日志级别（INFO/WARNING/ERROR等）
- `access_log_console`: 是否在控制台输出 uvicorn 访问日志（默认 true）；设为 false 可屏蔽 health、sessions、runs 等请求的 INFO 行，控制台更干净
- `request_logging`（可选）：请求日志中间件路径策略
  - `skip_info_prefixes`：路径前缀匹配时，Request/Stream started 等用 DEBUG，减少刷屏（默认含 `/health`、`/sessions`）
  - `always_info_prefixes`：路径前缀匹配时强制 INFO，覆盖 skip（调试会话时可加 `/sessions`）
  - 环境变量：`REQUEST_LOGGING_SKIP_INFO_PREFIXES`、`REQUEST_LOGGING_ALWAYS_INFO_PREFIXES`（逗号分隔前缀，覆盖配置）

### 数据库配置 (`database`)

```json
{
  "database": {
    "type": "sqlite|postgres|mysql",
    "path": "data/sessions.db",
    "url": "postgresql://user:pass@host:port/dbname",
    "pool_size": 10
  }
}
```

### 搜索配置 (`search`)

```json
{
  "search": {
    "milvus": {
      "host": "Milvus服务器地址",
      "port": 19530,
      "db_name": "default",
      "collection_brand": "品牌集合名称",
      "collection_category": "分类集合名称"
    },
    "qwen": {
      "api_key": "通义千问API密钥",
      "base_url": "API基础URL",
      "embedding_model": "text-embedding-v4",
      "rerank_model": "qwen3-rerank",
      "rerank_base_url": "Rerank API基础URL",
      "rerank_path": "/compatible-api/v1/reranks"
    },
    "default_params": {
      "enable_rerank": true,
      "category_top_k": 200,
      "category_top_n": 12,
      "timeout": 30
    }
  }
}
```

**字段说明**：
- `milvus`: Milvus 向量数据库配置
  - `host`: Milvus 服务器地址
  - `port`: Milvus 端口
  - `db_name`: 数据库名称
  - `collection_brand`: 品牌集合名称
  - `collection_category`: 分类集合名称
- `qwen`: 通义千问 API 配置
  - `api_key`: API密钥
  - `base_url`: API基础URL
  - `embedding_model`: 嵌入模型名称
  - `rerank_model`: 重排序模型名称
  - `rerank_base_url`: Rerank API基础URL
  - `rerank_path`: Rerank API路径
- `default_params`: 默认参数
  - `enable_rerank`: 是否启用重排序
  - `category_top_k`: 分类向量召回数量
  - `category_top_n`: 分类最终返回数量
  - `timeout`: 超时时间（秒）

### 查询标准化配置 (`query_normalization`)

```json
{
  "query_normalization": {
    "top_k": 200,
    "top_n": 12,
    "enable_rerank": true,
    "timeout": 30
  }
}
```

**字段说明**：
- `top_k`: 向量召回数量
- `top_n`: 最终返回数量
- `enable_rerank`: 是否启用 Rerank 精排
- `timeout`: 超时时间（秒）

### 节日工具配置 (`festival_tools`)

```json
{
  "festival_tools": {
    "days_ahead": 30
  }
}
```

**字段说明**：
- `days_ahead`: 查询未来多少天的节日信息（默认30天）

**相关配置**：
- 节日数据在 `tools/data/festivals_config.json` 中配置
- 每个节日包含权重（weight）字段，范围0-1，用于评估节日在电商营销场景中的重要性

### 推理工具配置 (`reasoning_tools`)

```json
{
  "reasoning_tools": {
    "add_instructions": true,
    "add_few_shot": false,
    "enable_think": true,
    "enable_analyze": true
  }
}
```

**字段说明**：
- `add_instructions`: 是否添加推理流程指令
- `add_few_shot`: 是否添加少样本示例
- `enable_think`: 是否启用 think 工具
- `enable_analyze`: 是否启用 analyze 工具

### 日志配置 (`logging`)

```json
{
  "logging": {
    "log_level": 1,
    "debug_level": "DEBUG",
    "log_dir": "log",
    "log_file": "app.log",
    "max_bytes": 10485760,
    "backup_count": 5
  }
}
```

**字段说明**：
- `log_level`: 调试级别（1或2，默认1）。当 `debug_level=DEBUG` 时生效
  - `1`: 只显示普通调试日志（`log_debug(..., log_level=1)`）
  - `2`: 显示所有调试日志（包括 `log_debug(..., log_level=2)`）
- `debug_level`: 控制台日志级别（DEBUG/INFO/WARNING/ERROR，默认INFO）
- `log_dir`: 日志目录（默认"log"，相对于 ecom_reco_agent 目录）
- `log_file`: 日志文件名（默认"app.log"）
- `max_bytes`: 单个日志文件最大字节数（默认10485760，即10MB）
- `backup_count`: 日志文件备份数量（默认5）

## 环境配置建议

### 开发环境 (dev.json)

- ✅ 启用调试模式
- ✅ 使用较低成本的模型（如 `qwen-plus`）
- ✅ 使用 SQLite 数据库
- ✅ 启用自动重载 (`reload: true`)
- ✅ 详细日志级别 (`DEBUG`)

### 演示环境 (show.json)

- ⚠️ 关闭调试模式
- ⚠️ 使用中等性能模型
- ⚠️ 使用 SQLite 或轻量级数据库
- ⚠️ 关闭自动重载
- ⚠️ 信息日志级别 (`INFO`)

### 生产环境 (prod.json)

- 🔒 关闭调试模式
- 🔒 使用高性能模型（如 `qwen-max`）
- 🔒 使用 PostgreSQL/MySQL 数据库
- 🔒 多进程部署 (`workers: 4`)
- 🔒 警告日志级别 (`WARNING`)
- 🔒 配置 CORS 和安全策略
- 🔒 启用速率限制

## 安全注意事项

⚠️ **重要**：生产环境配置包含敏感信息，请确保：

1. **不要将包含真实密钥的配置文件提交到 Git**
   - 将 `prod.json` 添加到 `.gitignore`
   - 使用密钥管理服务或加密配置

2. **配置文件权限**
   ```bash
   chmod 600 config/prod.json  # 仅所有者可读写
   ```

## 示例：配置模板

### 开发环境模板 (dev.json)

```json
{
  "llm": {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/",
    "api_key": "your-dev-api-key",
    "model_name": "qwen-plus",
    "model_type": "dashscope",
    "temperature": 0.2,
    "timeout": 120,
    "max_retries": 3
  },
  "api": {
    "base_url": "https://api-show.haoxiny.com/open/api/aiTrim",
    "timeout": 8.0,
    "max_results": 50,
    "max_retries": 0,
    "retry_delay": 1.0
  },
  "agent": {
    "num_history_runs": 10,
    "max_tool_calls_from_history": 0,
    "debug_mode": false,
    "stream": true,
    "stream_events": true,
    "enable_agentic_memory": true,
    "add_history_to_context": true,
    "markdown": true,
    "hitl_session_retention_days": 30
  },
  "agentos": {
    "port": 14466,
    "host": "0.0.0.0"
  },
  "search": {
    "milvus": {
      "host": "your-milvus-host",
      "port": 19530,
      "db_name": "default",
      "collection_brand": "your_brand_collection",
      "collection_category": "your_category_collection"
    },
    "qwen": {
      "api_key": "your-qwen-api-key",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "embedding_model": "text-embedding-v4",
      "rerank_model": "qwen3-rerank",
      "rerank_base_url": "https://dashscope.aliyuncs.com",
      "rerank_path": "/compatible-api/v1/reranks"
    },
    "default_params": {
      "enable_rerank": true,
      "category_top_k": 200,
      "category_top_n": 12,
      "timeout": 30
    }
  },
  "query_normalization": {
    "top_k": 200,
    "top_n": 12,
    "enable_rerank": true,
    "timeout": 30
  },
  "festival_tools": {
    "days_ahead": 30
  },
  "reasoning_tools": {
    "add_instructions": true,
    "add_few_shot": false,
    "enable_think": true,
    "enable_analyze": true
  },
  "logging": {
    "log_level": 2,
    "debug_level": "DEBUG",
    "log_dir": "log",
    "log_file": "app.log",
    "max_bytes": 10485760,
    "backup_count": 5
  }
}
```

### 生产环境模板 (prod.json)

```json
{
  "llm": {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/",
    "api_key": "your-real-api-key-here",
    "model_name": "qwen-max",
    "model_type": "dashscope",
    "temperature": 0.1,
    "timeout": 120,
    "max_retries": 5
  },
  "api": {
    "base_url": "https://api-prod.haoxiny.com/open/api/aiTrim",
    "timeout": 8.0,
    "max_results": 50,
    "max_retries": 3,
    "retry_delay": 1.0
  },
  "agent": {
    "num_history_runs": 10,
    "max_tool_calls_from_history": 0,
    "debug_mode": false,
    "stream": true,
    "stream_events": true,
    "enable_agentic_memory": true,
    "add_history_to_context": true,
    "markdown": true,
    "hitl_session_retention_days": 30
  },
  "agentos": {
    "port": 14466,
    "host": "0.0.0.0",
    "reload": false,
    "workers": 4,
    "log_level": "WARNING"
  },
  "search": {
    "milvus": {
      "host": "your-prod-milvus-host",
      "port": 19530,
      "db_name": "default",
      "collection_brand": "your_brand_collection",
      "collection_category": "your_category_collection"
    },
    "qwen": {
      "api_key": "your-prod-qwen-api-key",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "embedding_model": "text-embedding-v4",
      "rerank_model": "qwen3-rerank",
      "rerank_base_url": "https://dashscope.aliyuncs.com",
      "rerank_path": "/compatible-api/v1/reranks"
    },
    "default_params": {
      "enable_rerank": true,
      "category_top_k": 200,
      "category_top_n": 12,
      "timeout": 30
    }
  },
  "query_normalization": {
    "top_k": 200,
    "top_n": 12,
    "enable_rerank": true,
    "timeout": 30
  },
  "festival_tools": {
    "days_ahead": 30
  },
  "reasoning_tools": {
    "add_instructions": true,
    "add_few_shot": false,
    "enable_think": true,
    "enable_analyze": true
  },
  "logging": {
    "log_level": 1,
    "debug_level": "INFO",
    "log_dir": "log",
    "log_file": "app.log",
    "max_bytes": 10485760,
    "backup_count": 10
  },
  "database": {
    "type": "postgres",
    "url": "postgresql://user:pass@host:port/dbname",
    "pool_size": 10
  }
}
```

## 故障排查

### 问题：配置未生效

1. 检查 `domains.json` 中的域名配置
2. 确认环境特定配置文件存在且格式正确
3. 查看配置加载日志，确认使用的环境

### 问题：找不到配置文件

1. 确认配置文件在 `ecom_reco_agent/config/` 目录下
2. 检查文件权限
3. 查看日志中的配置加载信息

### 问题：配置加载失败

1. 检查 JSON 格式是否正确
2. 确认配置文件路径正确（应在 `ecom_reco_agent/config/` 目录下）
3. 查看 `config_loader.py` 的日志输出，确认使用的环境


