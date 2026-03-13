# AI自动装修助手（电商推品选品系统）

## 项目简介

AI自动装修助手是一个基于 Agno 框架的智能推荐系统，根据用户问题从真实商品库中查询并推荐适合的**品牌+品类**组合。支持节日场景智能识别、用户确认筛选、品类名称标准化等功能。

## 核心特性

- 🎯 **真实商品库查询**：只推荐商品库中真实存在的品牌+品类组合
- 🔍 **品类名称标准化**：使用 Milvus 向量搜索 + Qwen Rerank 精排，智能匹配用户输入的品类名称
- 🎨 **节日场景识别**：自动识别当前时间和临近节日，智能推断推荐场景
- ✅ **用户确认机制**：支持用户逐条确认/拒绝推荐，确保推荐精准度
- 🔄 **对话记忆支持**：支持继续对话场景，基于历史记录智能整合推荐结果
- 🌍 **多环境配置**：支持 dev/show/prod 多环境，自动根据域名/IP识别
- 📊 **Markdown 输出**：使用 Agno 官方方法，支持流式输出和 Markdown 渲染
- 📝 **统一日志系统**：完整的日志记录，支持文件和控制台双输出，可配置日志级别
- 🔗 **工具调用钩子**：自动记录所有工具调用信息，支持执行时间统计和查询汇总
- 📐 **分层提示词**：支持 layered 模式（按阶段动态装配 Prompt + `get_workflow_guidance`）与 legacy 静态流程，阶段与 Reference 可配置

## 目录结构

```
ai-automated-renovation/
├── ecom_reco_agent/              # 主项目目录
│   ├── agent/
│   │   ├── agent_os.py           # AgentOS 服务模块（Web 界面）
│   │   └── agent_os_mount.py     # AgentOS 挂载（FastAPI 集成）
│   ├── tools/
│   │   ├── brand_category_api_toolkit.py         # 品牌/分类关联查询工具
│   │   ├── query_normalization_toolkit.py         # 查询标准化工具（品类向量搜索+Rerank）
│   │   ├── festival_toolkit.py                    # 节日工具包（全量加载+内存缓存）
│   │   ├── recommendation_review_toolkit.py       # 推荐审核工具（验证、去重、字段生成）
│   │   ├── final_recommendation_sender_toolkit.py # 最终推荐数据发送工具
│   │   └── workflow_runtime_toolkit.py            # 运行时工作流工具（阶段指导、回退申请）
│   ├── prompts/
│   │   ├── __init__.py           # 提示词模块统一导出（支持 legacy / layered 模式）
│   │   ├── core.py               # 常驻核心约束
│   │   ├── reasoning.py          # 推理流程提示词
│   │   ├── workflow.py           # 静态工作流程与系统提示词（legacy 模式）
│   │   ├── builders/             # 分层提示词装配
│   │   │   ├── prompt_registry.py   # 阶段与 Reference 注册表
│   │   │   ├── prompt_loader.py     # 阶段/Reference 加载与装配
│   │   │   └── context_selector.py # 上下文选择（阶段、Reference）
│   │   ├── stages/               # 各阶段 Prompt（Markdown）
│   │   │   ├── stage_01_requirement.md ~ stage_07_confirmation.md
│   │   └── references/           # Reference 文档（品类、节日、数据格式等）
│   ├── events/
│   │   └── recommendation_event.py # 推荐数据自定义事件
│   ├── middleware/
│   │   └── request_logging.py    # 请求日志中间件
│   ├── config/
│   │   ├── config_loader.py      # 多环境配置加载器
│   │   ├── dev.json              # 开发环境配置
│   │   ├── show.json             # 演示环境配置
│   │   ├── prod.json             # 生产环境配置
│   │   └── domains.json          # 域名环境映射配置
│   ├── models/
│   │   └── model_factory.py      # 模型工厂（支持多种 LLM）
│   ├── utils/
│   │   ├── agno_logger.py        # Agno 日志配置模块
│   │   ├── tool_hooks.py         # 工具调用钩子（日志记录）
│   │   ├── workflow_controller.py # 运行时工作流控制器（阶段、回退、指导生成）
│   │   ├── recommendation_payload_validator.py # 推荐 payload 校验
│   │   └── db_cleanup.py         # 数据库清理工具
│   ├── documents/
│   │   ├── 接口开发说明文档.md    # 接口开发说明
│   │   ├── Runs 接口说明文档.md   # Runs 接口说明
│   │   ├── AGNO路由说明.md       # Agno 路由说明
│   │   ├── 日志系统说明.md        # 日志系统说明
│   │   └── 响应时间统计说明.md   # 响应时间统计说明
│   └── data/
│       └── hitl_sessions.db      # 会话数据库
├── search_data/                  # 搜索数据模块
│   ├── milvus_category_store.py  # Milvus 品类向量存储
│   ├── milvus_brand_store.py     # Milvus 品牌向量存储
│   ├── qwen_client.py            # Qwen API 客户端（Embedding + Rerank）
│   ├── config.py                 # 搜索配置
│   ├── category_utils.py         # 品类工具函数
│   ├── data/
│   │   └── mysql_data_source.py  # MySQL 数据源（节日数据）
│   └── rerank_instruct_category.txt  # 品类 Rerank 指令
├── web_ui_test/                  # 前端测试页面
├── test/                         # 测试文件
│   ├── AgentOS_API_Tests.postman_collection.json
│   └── AgentOS_API_Environment.postman_environment.json
├── bin/                          # 启动脚本（Linux/Mac）
│   ├── start.sh                  # 启动脚本
│   ├── status.sh                 # 状态检查脚本
│   ├── stop.sh                   # 停止脚本
│   └── restart.sh                # 重启脚本
├── start.py                      # 主启动脚本
├── requirements.txt              # 项目依赖
└── README.md                     # 项目说明文档
```

## 开发环境

### 环境要求

- Python 3.11+
- conda（推荐）或 venv

### 安装步骤

```bash
# 1. 创建conda环境（推荐在仓库根目录执行）
cd ai-automated-renovation
conda create -n ai-automated-renovation python=3.11 -y
conda activate ai-automated-renovation

# 2. 安装主项目依赖（若镜像源找不到 agno/dashscope，可加 -i https://pypi.org/simple）
pip install -r requirements.txt

# 3. 安装搜索数据模块依赖
cd search_data
pip install -r requirements.txt
cd ..

# 4. 可选：安装农历库（用于精确计算农历节日）
pip install zhdate

# 5. 可选：安装 Milvus 客户端（如果使用本地 Milvus）
pip install pymilvus
```

## 配置说明

### 多环境配置

项目支持多环境配置，通过 `ecom_reco_agent/config/config_loader.py` 自动根据域名/IP识别环境。每个环境使用独立的配置文件，配置项完全独立，不存在基础配置覆盖机制。

- **dev**：开发环境（默认），使用 `dev.json`
- **show**：演示环境，使用 `show.json`
- **prod**：生产环境，使用 `prod.json`

系统会自动识别环境，识别顺序：
1. 显式指定域名（代码中调用 `get_environment(domain="example.com")`）
2. 环境变量指定（设置 `DOMAIN=your-domain.com`）
3. 自动获取IP地址（系统自动获取当前机器IP，与 `domains.json` 配置匹配）
4. 手动指定环境（代码中调用 `load_config(environment="prod")`）
5. 默认环境（都不匹配时使用 `dev`）

详细的环境识别机制和配置说明请参考 [配置说明文档](ecom_reco_agent/config/README.md)。

### 配置文件结构

#### 开发环境配置（dev.json）

在 `ecom_reco_agent/config/dev.json` 中配置开发环境信息：

```json
{
  "llm": {
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/",
    "api_key": "your-api-key-here",
    "model_name": "qwen-plus",
    "temperature": 0.2,
    "timeout": 120,
    "max_retries": 3
  },
  "api": {
    "base_url": "https://api-show.haoxiny.com/open/api/aiTrim",
    "timeout": 8.0,
    "max_results": 50
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
      "collection_category": "your_collection"
    },
    "qwen": {
      "api_key": "your-qwen-api-key",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "embedding_model": "text-embedding-v4",
      "rerank_model": "qwen3-rerank"
    }
  },
  "logging": {
    "level": "INFO",
    "console_level": "WARNING",
    "file_level": "DEBUG",
    "log_dir": "log",
    "log_file": "app.log",
    "max_bytes": 10485760,
    "backup_count": 5
  }
}
```

#### 日志配置说明

- `level`: 根日志级别（默认 INFO）
- `console_level`: 控制台日志级别（默认 WARNING，减少输出）
- `file_level`: 文件日志级别（默认 DEBUG，记录所有信息）
- `log_dir`: 日志目录（默认 log，相对于 ecom_reco_agent 目录）
- `log_file`: 日志文件名（默认 app.log）
- `max_bytes`: 单个日志文件最大字节数（默认 10MB）
- `backup_count`: 保留的备份文件数量（默认 5 个）

#### 环境特定配置

- `show.json`：演示环境独立配置
- `prod.json`：生产环境独立配置
- `domains.json`：域名/IP到环境的映射配置

**注意**：每个环境的配置文件都是独立的，不存在覆盖关系。详细配置项说明请参考 [配置说明文档](ecom_reco_agent/config/README.md)。

### 配置加载

代码中通过 `config_loader` 统一加载配置：

```python
from config.config_loader import (
    get_llm_config, 
    get_api_config, 
    get_agentos_config,
    get_logging_config
)

# 自动根据域名/IP识别环境并加载配置
llm_config = get_llm_config()
api_config = get_api_config()
agentos_config = get_agentos_config()
logging_config = get_logging_config()
```

## 运行方式

### 方式 1：直接启动（推荐）

```bash
python start.py
```

启动后访问：
- **Web 界面**: http://localhost:14466
- **API 文档**: http://localhost:14466/docs
- **配置页面**: http://localhost:14466/config

在 Web 界面中可以直接与 Agent 对话，支持流式输出和实时调试。

**自定义端口和主机**：
配置在 `ecom_reco_agent/config/dev.json` 的 `agentos` 部分，或通过环境变量：
```bash
AGENTOS_PORT=8888 AGENTOS_HOST=127.0.0.1 python start.py
```

### 方式 2：使用启动脚本（Linux/Mac）

```bash
# 启动服务
./bin/start.sh

# 查看状态
./bin/status.sh

# 停止服务
./bin/stop.sh
```

### API 测试

项目提供了 Postman 测试集合，位于 `test/` 目录：
- `AgentOS_API_Tests.postman_collection.json` - API 测试集合
- `AgentOS_API_Environment.postman_environment.json` - 环境配置

导入 Postman 后即可运行 API 测试。

## 工具说明

### 1. 查询标准化工具（Query Normalization）

**文件**: `tools/query_normalization_toolkit.py`

使用 Milvus 向量搜索 + Qwen Rerank 精排，将用户输入的品类名称标准化为商品库中的标准品类名称。

**工具函数**：
- `search_category_by_name(category_name, top_k=200, top_n=12, enable_rerank=True, category_level=3)`：标准化品类查询，返回最匹配的标准品类列表
  - `category_level=1`：一级分类（粗颗粒度，如"家用电器"）
  - `category_level=2`：二级分类（中等颗粒度，如"大家电"）
  - `category_level=3`：三级分类（最细颗粒度，如"空调"，category_code 为 6 位数字）

**工作流程**：
1. 使用 Qwen Embedding 将用户查询向量化
2. 在 Milvus 中搜索相似品类（TopK）
3. 使用 Qwen Rerank 精排（TopN）
4. 返回标准化的品类名称和编码

**配置**：在 `config/dev.json` 的 `query_normalization` 部分配置。

### 2. 节日场景工具

**文件**: `tools/festival_toolkit.py`

在意图解析阶段，当用户未明确指定时间、节日或场景时，Agent 会自动调用此工具获取当前时间和所有节日数据，基于完整数据智能筛选匹配的节日场景。

**工具函数**：
- `get_festival_date_info()`：获取当前时间信息（公历、农历、季节、月份等）
- `get_all_festivals()`：获取所有节日数据（全量加载，使用内存缓存机制）
  - 返回所有节日数据，供模型基于当前时间和用户意图进行智能筛选
  - 使用内存缓存，支持自动刷新（TTL 24小时，刷新间隔可配置）

**工作方式**：
1. Agent 调用 `get_festival_date_info()` 获取当前时间信息
2. Agent 调用 `get_all_festivals()` 获取所有节日数据
3. 模型基于当前时间信息和用户意图，从所有节日数据中筛选匹配的节日场景
4. 提取 `festival_scenes`（必须包含 `festival_name` 和 `scene_type` 两个字段）

**使用场景**：
- 用户问题："推荐一些商品" → Agent 获取当前时间和所有节日数据，基于时间智能筛选匹配的节日场景
- 用户问题："春节快到了，推荐礼品" → Agent 从所有节日数据中筛选出"春节"相关的场景

**配置**：
- 节日数据表配置：通过环境变量 `BUSINESS_TABLE_FESTIVAL` 配置（默认：`skycrane_website.t_trim_festival_data`）
- 查询天数：在 `config/dev.json` 的 `festival_tools.days_ahead` 中配置（默认30天，用于说明查找范围）
- 缓存刷新间隔：在 `config/dev.json` 的 `festival_tools.cache_refresh_interval_hours` 中配置（默认24小时）

**缓存机制**：
- 使用模块级内存缓存，首次调用时全量加载所有节日数据
- TTL 硬限制为 24 小时，配置的刷新间隔不能超过 24 小时
- 每次调用时自动检查缓存是否过期，过期则自动刷新

### 3. 品牌/分类查询工具

**文件**: `tools/brand_category_api_toolkit.py`

封装真实商品库查询接口，提供品牌和分类的关联查询。

**工具函数**：
- `query_category_by_brand(brand_code, brand_name)`：根据品牌编码或名称查询该品牌在商品库中有货的分类列表
- `query_brand_by_category(category_code, category_name)`：根据分类编码或名称查询该分类在商品库中有货的品牌列表

**重要说明**：
- 这是真实商品库查询，返回空列表表示商品库中没有对应商品
- 禁止自行编造或补全未查询到的品牌/品类编码
- 只有查询到的品牌+品类组合才能推荐给用户

### 4. 推荐审核工具

**文件**: `tools/recommendation_review_toolkit.py`

提供推荐数据的验证、去重和字段生成功能。

**工具函数**：
- `build_review_fields(recommendations, festival_scenes)`：生成推荐列表数据
  - 验证原始数据（必须包含 brandCode 和 categoryCode）
  - 去重处理（基于 brandCode + categoryCode）
  - 生成推荐列表数据格式

**返回数据格式**：
```python
{
    "recommendations": [
        {
            "brandName": "品牌名称",
            "brandCode": "品牌编码",
            "categoryName": "品类名称",
            "categoryCode": "品类编码"
        }
    ],
    "festival_scenes": [
        {
            "festival_name": "春节",
            "scene_type": "节日营销"
        }
    ]
}
```

### 5. 最终推荐发送工具

**文件**: `tools/final_recommendation_sender_toolkit.py`

在用户确认后，通过自定义事件发送最终的推荐数据到前端。

**工具函数**：
- `send_final_recommendation_data(recommendations_data)`：发送最终推荐数据到前端
  - 接收 build_review_fields 返回的完整数据
  - 通过自定义事件在 runs 接口的流式响应中返回推荐数据

**工作流程**：
1. 在用户确认后接收 build_review_fields 返回的完整数据
2. 通过自定义事件（RecommendationDataEvent）发送到前端
3. 返回工具结果文本给模型用于生成聊天内容

### 6. 运行时工作流工具

**文件**: `tools/workflow_runtime_toolkit.py`

在分层提示词（layered）模式下，为 Agent 提供按轮次、按阶段的运行时指导，并支持查询回退申请。

**工具函数**：
- `get_workflow_guidance(user_input)`：根据当前用户输入返回本轮运行时阶段指导（当前阶段允许的工具与说明）
- `request_query_retry(reason)`：在查询结果不足时申请回退到品类标准化阶段，获批后可再次执行阶段 3
- `get_workflow_state_snapshot()`：返回当前工作流状态快照，便于调试

**使用约定**：每轮收到用户输入后，Agent 应先调用 `get_workflow_guidance`，再按指导中允许的工具执行；回退到品类标准化前需先调用 `request_query_retry`。

## 工作流程

Agent 的完整工作流程（7 个阶段）。在**分层（layered）模式**下，每轮需先调用 `get_workflow_guidance(user_input)` 获取当前阶段指导，再按指导执行。

1. **需求解析与规划阶段**
   - 使用 `think` 工具进行意图分析，识别品类、品牌、节日/场景信息
   - 判断是新需求还是继续对话（基于关键词识别和历史记录）
   - 若是继续对话，提取历史记录中的 `build_review_fields` 返回结果
   - 智能规划后续执行策略

2. **节日推荐阶段**
   - 调用 `get_festival_date_info()` 获取当前时间信息（公历、农历、季节等）
   - 调用 `get_all_festivals()` 获取所有节日数据（全量加载，使用内存缓存）
   - 基于当前时间信息和用户意图，从所有节日数据中筛选匹配的节日场景
   - 从筛选结果中提取 `festival_scenes`（必须包含 `festival_name` 和 `scene_type`）
   - 保存所有匹配的记录对，禁止根据语义相似性去重

3. **品类标准化阶段**
   - 调用 `search_category_by_name` 进行品类标准化
   - 优先选择最细颗粒度品类（category_level=3）
   - 如果粗颗粒度品类占比较高，进行细化推荐（推断细分类别并再次标准化）
   - 保存完整的 `normalized_results` 列表

4. **数据库查询规划阶段**
   - 调用 think 工具分析品类标准化结果
   - 评估各品类的 rerank_score 和 category_level
   - 结合节日/场景信息，决定查询哪些品类
   - 优先选择 category_level=3 的品类（最细颗粒度）进行查询

5. **查询商品库阶段**
   - 从 normalized_results 中选取最细颗粒度（category_level=3）的品类
   - 并行调用 `query_brand_by_category` 查询品牌列表
   - 合并所有非空查询结果，基于 brandCode 与 categoryCode 去重
   - **回退细化机制**：如果查询结果为空或不够丰富，回退到第3步进行细化推荐

6. **结果整合与输出阶段**
   - 使用 think 工具分析用户需求与历史记录，确定整合策略
   - 根据不同场景（增加品类、删除/筛选、修改品类、新需求）整合新旧数据
   - 调用 `build_review_fields` 传入整合后的最终数据
   - 调用 `analyze` 工具生成推荐摘要并输出
   - 阻塞等待用户调整或确认

7. **最终确认阶段**
   - 调用 think 工具判断用户回复的意图
   - **分支1**（肯定确认）：调用 `send_final_recommendation_data` 发送最终结果，然后调用 `analyze` 生成最终摘要
   - **分支2**（其他情况）：在 think 工具中给出决策建议，跳转回第一阶段

## 提示词架构

项目支持两种提示词模式：**legacy**（静态完整流程）与 **layered**（分层按阶段装配，默认）。

### 分层模式（layered，默认）

- **核心约束**：`prompts/core.py` 中的 `CORE_PROMPT`（角色、数据真实性、阶段遵守、语言等）
- **运行时规则**：在 `prompt_loader.build_layered_system_prompt()` 中拼接，要求每轮先调用 `get_workflow_guidance`、只执行当前阶段允许的工具、回退前需 `request_query_retry` 等
- **阶段 Prompt**：`prompts/stages/` 下 `stage_01_requirement.md`～`stage_07_confirmation.md`，由 `workflow_controller` 与 `prompt_loader` 按当前阶段加载
- **Reference**：`prompts/references/` 下的品类、节日、数据格式、继续对话、输出风格等说明，按阶段在 `prompt_registry` 中配置默认引用，由 `context_selector` 与 `prompt_loader` 装配摘要
- **装配流程**：`prompts/builders/prompt_loader.py` 的 `build_layered_prompt(context)` 根据 `PromptContext`（当前阶段、是否继续对话、是否需要数据格式/输出风格等）选择阶段与 Reference，生成当轮系统提示

### 静态模式（legacy）

- **文件**：`prompts/workflow.py`（`SYSTEM_PROMPT`、`WORKFLOW`、`COMPLETE_WORKFLOW`）与 `prompts/reasoning.py`（`REASONING_INSTRUCTIONS`）
- **内容**：7 阶段完整流程的静态文本，工具说明写在各阶段描述中

### 模块说明

| 路径 | 说明 |
|------|------|
| `prompts/__init__.py` | 统一导出；默认 `SYSTEM_INSTRUCTIONS` 使用 layered，`build_system_instructions(mode)` 可切换 legacy/layered |
| `prompts/core.py` | 常驻核心约束 |
| `prompts/builders/prompt_registry.py` | 阶段与 Reference 定义（`STAGE_DEFINITIONS`、`REFERENCE_DEFINITIONS`） |
| `prompts/builders/context_selector.py` | 根据 `PromptContext` 选择当前阶段与 Reference 列表 |
| `prompts/builders/prompt_loader.py` | 读取 stage/reference 文件并装配为 `PromptBundle`，提供 `build_layered_system_prompt()` |

### 使用方式

```python
from prompts import SYSTEM_INSTRUCTIONS, build_system_instructions, REASONING_INSTRUCTIONS

# 默认使用分层模式（与 get_workflow_guidance 配合）
agent = Agent(instructions=SYSTEM_INSTRUCTIONS, ...)

# 或显式指定 legacy 静态流程
instructions = build_system_instructions("legacy")
agent = Agent(instructions=f"{instructions}\n\n{REASONING_INSTRUCTIONS}", ...)
```

## 事件系统

项目使用自定义事件机制在流式响应中返回推荐数据。

### 推荐数据事件

**文件**: `events/recommendation_event.py`

**类名**: `RecommendationDataEvent`

**功能**: 在 runs 接口的流式响应中返回推荐数据

**数据格式**:
```python
{
    "recommendations": [
        {
            "brandName": "品牌名称",
            "brandCode": "品牌编码",
            "categoryName": "品类名称",
            "categoryCode": "品类编码",
            "value": True  # True=启用，False=删除
        }
    ],
    "festival_scenes": [
        {
            "festival_name": "节日名称",
            "scene_type": "场景类型"
        }
    ]
}
```

**使用方式**:
在 `send_final_recommendation_data` 工具中通过 yield 发送事件：
```python
yield RecommendationDataEvent(data=complete_data)
```

前端可以通过监听流式响应中的自定义事件来接收推荐数据。

## 日志系统

项目使用 Agno 框架的标准日志系统，所有日志记录在 `ecom_reco_agent/log/app.log` 文件中，同时支持控制台彩色输出。此外，系统还提供了工具调用钩子机制，自动记录所有工具的调用信息。

### 日志级别

- **DEBUG**: 详细的调试信息（仅文件日志）
- **INFO**: 重要信息（服务启动、配置加载等，仅文件日志）
- **WARNING**: 警告信息（控制台和文件）
- **ERROR**: 错误信息（控制台和文件）
- **CRITICAL**: 严重错误（控制台和文件）

### Agno 日志特性

- 控制台输出使用 RichHandler，支持彩色显示
- 文件日志使用 RotatingFileHandler，支持日志轮转
- 支持动态调整日志级别（运行时修改）

### 工具调用钩子

项目提供了工具调用钩子机制（`utils/tool_hooks.py`），自动记录所有工具的调用信息：

**功能特性**：
- 自动记录所有工具调用的参数、结果和执行时间
- 统计查询商品库阶段的汇总信息（查询品类数、返回品牌数、总耗时）
- 支持 DEBUG 级别的详细日志记录（level=2）
- 格式化输出，避免参数和结果过长

**使用方式**：
```python
from utils.tool_hooks import create_tool_hook

# 在 Agent 初始化时传入 tool_hooks 参数
agent = Agent(
    tools=[...],
    tool_hooks=create_tool_hook()
)
```

**日志格式**：
```
[TOOL_CALL] 工具: query_brand_by_category | 状态: 成功 | 耗时: 0.523s | 参数: {"category_code": "123456"} | 结果: [{"brandCode": "MIDEA", ...}]
```

### 日志配置

日志配置在 `ecom_reco_agent/config/dev.json` 的 `logging` 部分：

```json
{
  "logging": {
    "level": "INFO",
    "console_level": "WARNING",
    "file_level": "DEBUG",
    "log_dir": "log",
    "log_file": "app.log",
    "max_bytes": 10485760,
    "backup_count": 5
  }
}
```

### 日志轮转

日志文件按大小自动轮转：
- 单个文件最大 10MB（可配置）
- 保留 5 个备份文件（可配置）
- 备份文件位于 `ecom_reco_agent/log/` 目录
- 备份文件命名：`app.log.1`, `app.log.2`, ...

### 使用日志

在代码中使用日志（基于 Agno 日志系统）：

```python
from agno.utils.log import log_info, log_warning, log_error, log_exception

log_info("服务启动成功")
log_warning("配置项缺失，使用默认值")
log_error("API 调用失败")
# 对于异常，使用 log_exception
try:
    # 可能出错的代码
    pass
except Exception:
    log_exception("API 调用失败")
```

## 使用示例

启动 Web 界面后（`python start.py`），在浏览器中访问 http://localhost:14466，可以直接与 Agent 对话。

### 示例 1：节日场景推荐

在 Web 界面中输入：
```
春节快到了，推荐一些适合送礼的商品
```

Agent 会：
1. 识别"春节"场景
2. 查询适合春节送礼的品牌+品类组合
3. 调用 `build_review_fields` 生成推荐数据
4. 调用 `analyze` 工具生成推荐摘要
5. 等待用户确认

用户确认后：
1. 调用 `send_final_recommendation_data` 发送最终结果
2. 调用 `analyze` 生成最终推荐摘要

### 示例 2：未指定场景的推荐

在 Web 界面中输入：
```
推荐一些热销商品
```

Agent 会：
1. 调用 `get_festival_date_info()` 获取当前时间信息
2. 调用 `get_all_festivals()` 获取所有节日数据
3. 基于当前时间和用户意图，从所有节日数据中筛选匹配的节日场景（如"情人节"、"春节"等）
4. 基于筛选的场景进行推荐

### 示例 3：品类名称标准化

在 Web 界面中输入：
```
推荐一些厨房电器的商品
```

Agent 会：
1. 调用 `search_category_by_name` 将"厨房电器"标准化为商品库中的标准品类
2. 使用标准化后的品类查询品牌
3. 如果查询结果不够丰富，触发回退细化机制
4. 输出推荐结果

### 示例 4：继续对话（增加品类）

在 Web 界面中输入：
```
加上美的的空调
```

Agent 会：
1. 识别为继续对话场景（关键词"加上"）
2. 从历史记录中提取 `build_review_fields` 的返回结果
3. 查询"美的"品牌的"空调"品类
4. 合并新旧推荐数据（基于 brandCode + categoryCode 去重）
5. 调用 `build_review_fields` 生成整合后的推荐数据
6. 调用 `analyze` 生成更新后的推荐摘要

### 示例 5：品牌维度查询

在 Web 界面中输入：
```
查询美的品牌有哪些品类
```

Agent 会：
1. 调用 `query_category_by_brand(brand_name="美的")`
2. 返回该品牌在商品库中有货的所有分类

## 注意事项

1. **真实商品库约束**：只有查询到的品牌+品类组合才能推荐，禁止编造数据
2. **数据真实性要求**：输出的数据标签结果必须严格从数据库工具查询结果中获取，绝对禁止编造或推断
3. **环境配置**：各环境（dev/show/prod）使用独立配置文件，不存在互相覆盖；通过域名/IP 或环境变量识别当前环境
4. **农历支持**：安装 `zhdate` 库可获得更精确的农历节日计算
5. **用户确认**：推荐必须经过用户确认后才能输出最终结果
6. **日志文件**：日志文件存储在 `ecom_reco_agent/log/` 目录，已配置 `.gitignore` 忽略
7. **工具调用顺序**：Agent 会严格按照工作流程的 7 个阶段执行，确保工具调用顺序正确
8. **历史记录处理**：继续对话场景下，系统会自动从历史记录中提取之前的推荐数据进行整合
9. **回退细化机制**：如果查询结果为空或不够丰富，系统会自动触发回退细化机制，最多执行 2 轮

## 故障排查

### 问题：无法导入 agno 模块

**解决**：确保使用官方 PyPI 源安装（版本以 `requirements.txt` 为准）：
```bash
pip install -i https://pypi.org/simple -r requirements.txt
```

### 问题：端口被占用

**解决**：修改 `ecom_reco_agent/config/dev.json` 中的 `agentos.port`，或使用环境变量：
```bash
AGENTOS_PORT=8888 python start.py
```

### 问题：API Key 未配置

**解决**：在 `ecom_reco_agent/config/dev.json` 的 `llm.api_key` 中填写你的 DashScope API Key。

### 问题：Milvus 连接失败

**解决**：检查 `ecom_reco_agent/config/dev.json` 的 `search.milvus` 配置，确保 Milvus 服务可访问。

### 问题：日志文件未生成

**解决**：检查 `ecom_reco_agent/log/` 目录权限，确保应用有写入权限。日志目录会在首次运行时自动创建。

## 相关文档

- [Agno 官方文档](https://github.com/agno-ai/agno)
- [配置说明](ecom_reco_agent/config/README.md)
- [接口开发说明](ecom_reco_agent/documents/接口开发说明文档.md)
- [Runs 接口说明](ecom_reco_agent/documents/Runs 接口说明文档.md)
- [AGNO 路由说明](ecom_reco_agent/documents/AGNO路由说明.md)
- [日志系统说明](ecom_reco_agent/documents/日志系统说明.md)
- [响应时间统计说明](ecom_reco_agent/documents/响应时间统计说明.md)
