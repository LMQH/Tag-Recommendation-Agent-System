# AI 自动装修助手 - Codex 持久记忆文档

## 项目概述

**项目名称**：AI自动装修助手（电商推品选品系统）

**技术栈**：Python 3.11+、Agno 2.3.21、Qwen Plus、Milvus、MySQL、FastAPI、Uvicorn

---

## 核心规则（必须遵守）

### 1. 语言规则 ⚠️ 最重要
**所有回复给用户的说明文字部分必须使用中文，禁止使用英文。**

- ✅ 正确：`日志文件已生成，共记录 5 条错误`
- ❌ 错误：`Log file generated, 5 errors recorded`

**例外**：代码内容（变量名、函数名）、技术术语（API、JSON、SQL）、命令行输出

### 2. 数据真实性原则
- 只推荐商品库中真实存在的品牌+品类组合
- 禁止自行编造或补全未查询到的数据
- 输出的数据标签必须严格从数据库工具查询结果中获取

### 3. 编码规范
- 函数文档字符串使用中文
- 日志消息使用中文
- 使用类型注解（Type Hints）
- 异常处理要完整，包含详细日志
- 使用配置加载器统一管理配置

---

## 项目结构速查

```
ai-automated-renovation/
├── ecom_reco_agent/              # 主项目
│   ├── agent/                    # Agent 模块
│   │   ├── agent_os.py          # AgentOS 服务
│   │   └── agent_os_mount.py    # AgentOS 挂载配置
│   ├── tools/                    # 工具包
│   │   ├── brand_category_api_toolkit.py      # 品牌品类查询工具
│   │   ├── festival_toolkit.py              # 节日工具
│   │   ├── query_normalization_toolkit.py   # 品类标准化工具
│   │   ├── recommendation_review_toolkit.py # 推荐审查工具
│   │   └── final_recommendation_sender_toolkit.py # 最终推荐发送工具
│   ├── prompts/                  # 提示词模块
│   │   ├── reasoning.py         # 推理提示词
│   │   └── workflow.py          # 工作流提示词
│   ├── events/                   # 事件系统
│   │   └── recommendation_event.py
│   ├── middleware/               # 中间件
│   │   └── request_logging.py   # 请求日志中间件
│   ├── models/                   # 模型模块
│   │   └── model_factory.py     # 模型工厂
│   ├── config/                   # 多环境配置（dev/show/prod）
│   ├── utils/                    # 工具类
│   │   ├── agno_logger.py       # Agno 日志系统
│   │   ├── tool_hooks.py        # 工具钩子
│   │   └── db_cleanup.py        # 数据库清理工具
│   ├── data/                     # 数据目录
│   ├── log/                      # 日志目录
│   └── documents/                # 文档目录
├── search_data/                  # 搜索数据模块（Milvus、Qwen）
├── start.py                      # 主启动脚本
└── README.md                     # 项目说明文档
```

---

## 关键配置

### 环境配置
- 每个环境的配置文件都是**独立**的，不存在覆盖关系
- 环境识别顺序：显式域名 → 环境变量 → 自动IP匹配 → 手动指定 → 默认dev

### 重要环境变量
- `BUSINESS_TABLE_FESTIVAL`：节日数据表配置（默认：`skycrane_website.t_trim_festival_data`）

### 日志配置
- 日志位置：`ecom_reco_agent/log/app.log`
- 日志级别：DEBUG、INFO、WARNING、ERROR、CRITICAL
- 使用 Agno 日志系统：`from agno.utils.log import log_info, log_warning, log_error`

### AgentOS 配置
- 配置项：`agentos.port`（默认 14466）
- 配置项：`agentos.host`（默认 0.0.0.0）
- 支持流式响应：默认启用
- 内置 CORS 配置：自动处理跨域请求

### 中间件配置
- 请求日志中间件：默认启用
- 自动记录所有 API 请求和响应
- 与 Agno 日志系统集成

---

## 重要工具说明

### 节日工具（festival_toolkit.py）
- 使用**全量加载+内存缓存**机制
- 缓存刷新间隔可配置（默认24小时）
- 已修复问题：移除了 `WHERE is_deleted = 0` 条件
- 推荐使用 `get_all_festivals()` 而非已废弃的 `query_festival_by_name()`

### 品类标准化工具（query_normalization_toolkit.py）
- 使用 Milvus 向量搜索 + Qwen Rerank 精排
- category_level=3 为最细颗粒度（6位数字编码）

### 推荐审查工具（recommendation_review_toolkit.py）
- 对推荐结果进行审查和验证
- 确保推荐数据的真实性和准确性
- 支持多维度质量检查

### 最终推荐发送工具（final_recommendation_sender_toolkit.py）
- 处理最终推荐结果的发送
- 支持流式响应包装
- 优化时间计算与记录

---

## 新功能特性

### 流式响应包装
- 支持流式输出，提升用户体验
- 优化响应时间计算和记录
- 适配长文本生成场景

### CORS 配置优化
- 使用 AgentOS 内置 CORS 配置
- 移除外部 CORS 中间件，简化配置
- 适配 Nginx 反向代理场景
- 支持 path_prefix + app.mount() 模式

### 请求日志中间件
- 自动记录所有 HTTP 请求和响应
- 记录请求方法、路径、客户端IP
- 记录响应状态码和处理时间
- 复用 Agno 日志系统，统一日志管理

### 模型工厂模式
- 根据配置自动创建合适的模型实例
- 支持 DashScope、OpenAI、DeepSeek 等多种模型
- 统一的模型加载和配置接口

---

## 常见问题

### get_all_festivals 返回空结果
1. 检查数据库连接配置
2. 检查环境变量 `BUSINESS_TABLE_FESTIVAL`
3. 查看日志文件 `ecom_reco_agent/log/app.log`

### 无法导入 agno 模块
```bash
pip install -i https://pypi.org/simple agno==2.3.21
```

### CORS 跨域问题
- 确认使用 AgentOS 内置 CORS 配置
- 检查 Nginx 反向代理配置是否正确
- 验证 `path_prefix` 设置是否正确
- 查看日志文件排查具体错误

### 流式响应异常
- 检查客户端是否支持 SSE（Server-Sent Events）
- 确认网络连接稳定
- 查看日志中的时间计算记录
- 验证响应包装器是否正常工作

### 端口被占用
```bash
# Windows
netstat -ano | findstr :14466
taskkill /PID <进程ID> /F

# Linux/Mac
lsof -ti:14466 | xargs kill -9
```

---

## 开发注意事项

### 代码规范
- 所有新增代码必须包含类型注解
- 函数文档字符串使用中文
- 使用 Agno 日志系统，不要使用 `print()`
- 异常处理要完整，包含详细的错误日志

### 工具开发
- 新工具放在 `ecom_reco_agent/tools/` 目录
- 使用工厂模式创建工具实例
- 遵循现有工具的命名规范
- 在 `tools/__init__.py` 中导出新工具

### 配置管理
- 新增配置项请在对应环境的配置文件中添加
- 配置文件路径：`ecom_reco_agent/config/environments/`
- 使用 `config_loader` 统一加载配置
- 敏感信息使用环境变量

### 测试建议
- 使用 FastAPI 自动生成的文档进行测试：`/docs`
- 使用 Postman Collection 进行 API 测试
- 查看日志文件排查问题
- 使用不同环境配置进行测试

---

```bash
python start.py
```

### 访问地址
- **Web 界面**: http://localhost:14466
- **API 文档**: http://localhost:14466/docs
- **配置页面**: http://localhost:14466/config

### 端口配置
- 默认端口：14466
- 可在配置文件中修改 `agentos.port` 参数
- 支持通过环境变量覆盖配置

---

## 文档参考

### 官方文档
- [Agno 官方文档](https://github.com/agno-ai/agno)

### 项目文档
- [配置说明](../ecom_reco_agent/config/README.md) - 多环境配置说明
- [接口开发说明文档](../ecom_reco_agent/documents/接口开发说明文档.md) - API 接口开发指南
- [AGNO路由说明](../ecom_reco_agent/documents/AGNO路由说明.md) - AgentOS 路由配置说明
- [Runs 接口说明文档](../ecom_reco_agent/documents/Runs%20接口说明文档.md) - Runs 接口使用说明
- [日志系统说明](../ecom_reco_agent/documents/日志系统说明.md) - 日志系统使用指南
