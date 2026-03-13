"""
AI自动装修助手 - Agent 模块
提供 Agent 和 AgentOS 的创建和初始化

mount 挂载模式，用于将 AgentOS 挂载到 FastAPI 应用中
现在这个模式已经废弃，不推荐使用
"""

import sys
import warnings
from pathlib import Path

# 忽略 httpx 客户端销毁时的 AttributeError 警告（openai 1.85.0 与 httpx 0.27.x 兼容性问题）
warnings.filterwarnings("ignore", message=".*SyncHttpxClientWrapper.*")

from agno.os import AgentOS
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools
from agno.tools.user_control_flow import UserControlFlowTools
from agno.db.sqlite import SqliteDb
from fastapi import FastAPI

# 初始化日志系统（必须在其他导入之前）
try:
    from config.config_loader import get_logging_config  # type: ignore
    from utils.agno_logger import setup_agno_logging_from_config  # type: ignore
    from agno.utils.log import log_info, log_debug, log_warning  # type: ignore
except ImportError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from config.config_loader import get_logging_config  # type: ignore
    from utils.agno_logger import setup_agno_logging_from_config  # type: ignore
    from agno.utils.log import log_info, log_debug, log_warning  # type: ignore

# 初始化日志系统
logging_config = get_logging_config()
setup_agno_logging_from_config(logging_config)

# 兼容直接脚本运行与包导入
try:
    from tools import (
        create_brand_category_api_toolkit,
        create_recommendation_review_toolkit,
        create_final_recommendation_sender_toolkit,
        create_query_normalization_toolkit,
        create_workflow_runtime_toolkit,
    )  # type: ignore
except ImportError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from tools import (
        create_brand_category_api_toolkit,
        create_recommendation_review_toolkit,
        create_final_recommendation_sender_toolkit,
        create_query_normalization_toolkit,
        create_workflow_runtime_toolkit,
    )  # type: ignore

# 提示词集中管理
try:
    from prompts import REASONING_INSTRUCTIONS, build_system_instructions  # type: ignore
except ImportError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from prompts import REASONING_INSTRUCTIONS, build_system_instructions  # type: ignore

# ecom_reco_agent/agent/ -> ecom_reco_agent/
BASE_DIR = Path(__file__).resolve().parents[1]

# 模型相关导入
try:
    from models import create_model, load_llm_config  # type: ignore
except ImportError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from models import create_model, load_llm_config  # type: ignore


def create_ecom_reco_agent() -> Agent:
    """创建AI自动装修 Agent"""
    llm = load_llm_config()
    
    # 使用模型工厂创建模型实例
    model = create_model(llm)

    from config.config_loader import (
        get_api_config, 
        get_search_config, 
        get_reasoning_tools_config
    )
    api_config = get_api_config()
    from config.config_loader import get_agent_config, get_logging_config
    agent_config = get_agent_config()
    brand_category_toolkit = create_brand_category_api_toolkit(
        base_url=api_config.get("base_url", "https://api-show.haoxiny.com/open/api/aiTrim"),
        timeout=float(api_config.get("timeout", 8.0)),
        max_results=int(api_config.get("max_results", 50)),
    )
    recommendation_review_toolkit = create_recommendation_review_toolkit()

    # 数据发送工具配置（不再需要HTTP配置，数据通过自定义事件返回）
    final_recommendation_sender_toolkit = create_final_recommendation_sender_toolkit()
    workflow_runtime_toolkit = create_workflow_runtime_toolkit(
        max_retry_count=int(agent_config.get("max_query_retry_count", 2))
    )
    
    # 从配置读取推理工具参数
    reasoning_config = get_reasoning_tools_config()
    reasoning_tools = ReasoningTools(
        instructions=REASONING_INSTRUCTIONS,
        add_instructions=reasoning_config.get("add_instructions", True),
        add_few_shot=reasoning_config.get("add_few_shot", False),
        enable_think=reasoning_config.get("enable_think", True),
        enable_analyze=reasoning_config.get("enable_analyze", True),
    )

    # 查询标准化工具（Milvus 向量搜索 + Qwen Rerank）
    from config.config_loader import get_query_normalization_config
    search_config = get_search_config()
    query_norm_config = get_query_normalization_config()
    query_normalization_toolkit = create_query_normalization_toolkit(
        milvus_host=search_config.get("milvus", {}).get("host"),
        milvus_port=search_config.get("milvus", {}).get("port"),
        milvus_db_name=search_config.get("milvus", {}).get("db_name"),
        qwen_api_key=search_config.get("qwen", {}).get("api_key"),
        qwen_base_url=search_config.get("qwen", {}).get("base_url"),
        qwen_rerank_base_url=search_config.get("qwen", {}).get("rerank_base_url"),
        qwen_rerank_path=search_config.get("qwen", {}).get("rerank_path"),
        qwen_rerank_model=search_config.get("qwen", {}).get("rerank_model"),
        enable_rerank=query_norm_config.get("enable_rerank", True),
        timeout=query_norm_config.get("timeout", 30)
    )

    # 日期节日工具
    from tools import get_festivals_nearby, get_festival_date_info, get_all_festivals, save_matched_festivals, query_festival_by_name, query_festivals_by_scene
    
    # HITL 需要持久化 run 状态，确保用户确认后可继续执行
    db_path = BASE_DIR / "data" / "hitl_sessions.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 定期清理过期会话（每次启动时检查）
    try:
        from utils.db_cleanup import cleanup_expired_sessions
        from config.config_loader import get_agent_config
        agent_config_for_cleanup = get_agent_config()
        days_to_keep = agent_config_for_cleanup.get("hitl_session_retention_days", 30)
        
        deleted = cleanup_expired_sessions(
            db_path=db_path,
            session_table="ecom_reco_sessions",
            days_to_keep=days_to_keep,
            dry_run=False,
        )
        if deleted > 0:
            log_info(f"清理了 {deleted} 条过期 HITL 会话记录（保留 {days_to_keep} 天）")
    except Exception as e:
        log_warning(f"清理过期会话时出错（不影响启动）: {e}")
    
    db = SqliteDb(
        db_url=f"sqlite:///{db_path}",
        session_table="ecom_reco_sessions",
    )
 
    # 从配置读取Agent参数
    prompt_mode = agent_config.get("prompt_mode", "layered")

    # 根据配置构建系统提示词
    combined_instructions = build_system_instructions(prompt_mode=prompt_mode)
    
    # 从日志配置获取 debug_level 和 log_level，用于设置 Agent 的 debug_mode 和 debug_level
    logging_config = get_logging_config()
    debug_level = logging_config.get("debug_level", "INFO")
    log_level = logging_config.get("log_level", 1)
    
    # 确保 log_level 是有效的整数值（1 或 2）
    if not isinstance(log_level, int):
        try:
            log_level = int(log_level)
        except (ValueError, TypeError):
            log_level = 1
    if log_level not in (1, 2):
        log_level = 1
    
    # 根据 debug_level 确定 Agent 的 debug_mode
    # debug_level="DEBUG" 时，设置 debug_mode=True，否则使用 agent_config 中的配置
    if isinstance(debug_level, str) and debug_level.upper() == "DEBUG":
        agent_debug_mode = True
        agent_debug_level = log_level  # 使用配置的 log_level（1 或 2）
    else:
        # 非 DEBUG 级别时，使用 agent_config 中的 debug_mode 配置
        agent_debug_mode = agent_config.get("debug_mode", True)
        agent_debug_level = None  # 不设置 debug_level 参数
    
    # 创建工具调用钩子，用于记录所有工具调用日志
    from utils.tool_hooks import create_tool_hook, log_time_to_first_token_post_hook
    tool_hook = create_tool_hook()
    
    # 构建 Agent 参数字典
    agent_kwargs = {
        "id": "ecom-reco-agent",
        "name": "AI自动装修助手",
        "role": "AI自动装修助手：根据问题推荐数据标签。",
        "description": "面向电商推品/选品场景，输出品数据标签以及推荐摘要。",
        "model": model,
        "instructions": combined_instructions,
        "markdown": agent_config.get("markdown", True),
        "debug_mode": agent_debug_mode,
        "stream": agent_config.get("stream", True),
        "stream_events": agent_config.get("stream_events", True),
        "db": db,
        "update_memory_on_run": True,
        "enable_agentic_memory": agent_config.get("enable_agentic_memory", True),
        "add_history_to_context": agent_config.get("add_history_to_context", True),
        "num_history_runs": agent_config.get("num_history_runs", 10),
        "max_tool_calls_from_history": agent_config.get("max_tool_calls_from_history", 0),
        "tools": [
            reasoning_tools,  # 推理工具（包含 think 和 analyze）
            workflow_runtime_toolkit,  # 运行时工作流控制工具
            query_normalization_toolkit,  # 查询标准化工具（品类向量搜索 + Rerank）
            brand_category_toolkit,  # 品牌品类查询工具
            recommendation_review_toolkit,  # 推荐工具（验证和字段生成）
            final_recommendation_sender_toolkit,  # 最终推荐数据发送工具
            get_festivals_nearby,  # 获取节日信息工具
            get_festival_date_info,  # 获取节日日期信息工具
            get_all_festivals,  # 获取所有节日数据工具（全量加载）
            save_matched_festivals,  # 保存筛选后的节日到会话变量
            # query_festival_by_name,  # 查询节日名称信息工具（已废弃，保留待后续使用）
            # query_festivals_by_scene  # 查询节日场景信息工具（已废弃，保留待后续使用）
        ],
        "tool_hooks": [tool_hook],  # 使用Agno框架的tool_hooks参数，统一记录所有工具调用日志
        "post_hooks": [log_time_to_first_token_post_hook],
        "retries": int(llm.get("max_retries", 0) or 0),  # 最大重试次数
    }
    
    # 如果设置了 debug_level，添加到参数中
    if agent_debug_level is not None:
        agent_kwargs["debug_level"] = agent_debug_level
    
    agent = Agent(**agent_kwargs)

    log_debug("Tool_hooks 工具钩子已注册成功", log_level=1)

    return agent


def create_agent_os() -> AgentOS:
    """创建 AgentOS 实例"""
    agent = create_ecom_reco_agent()

    # 由测试脚本可知，Nginx 已配置 CORS
    # 注意：AgentOS 框架即使不传 cors_allowed_origins 也会使用默认值并添加 CORS 中间件
    # 这是框架的限制，但 Nginx 层的 CORS 配置会优先处理
    agent_os = AgentOS(
        name="AI自动装修助手",
        description="AI自动装修助手 - 根据用户问题推荐数据标签",
        agents=[agent],
        cors_allowed_origins=["*"],  # 内置支持，允许所有来源
    )

    return agent_os


# 在模块级别创建 AgentOS 实例和 app
# 使用检查机制防止重复初始化（当模块被重新导入时）
_module_name = __name__
_module = sys.modules.get(_module_name)

# 检查是否已经初始化（通过检查模块属性）
if not hasattr(_module, "_agent_os_initialized"):  # type: ignore
    log_info("=" * 80)
    log_info("🚀 初始化AI自动装修 AgentOS 服务")
    log_info("=" * 80)

    # 创建 AgentOS 实例
    agent_os = create_agent_os()

    # 获取 FastAPI 应用（必须在模块级别）
    agent_app = agent_os.get_app()

    # 从配置读取路径前缀（用于 Nginx 反向代理场景）
    from config.config_loader import get_agentos_config
    agentos_config = get_agentos_config()
    path_prefix = agentos_config.get("path_prefix", "")

    # 如果配置了路径前缀，创建一个包装应用
    if path_prefix:
        from fastapi import FastAPI
        
        app = FastAPI(
            title=agent_app.title,
            description=agent_app.description,
            version=agent_app.version
        )

        # CORS 确保跨域请求正常工作
        # 注意：重复的 CORS 头会影响功能（Nginx 已配置）
        # from fastapi.middleware.cors import CORSMiddleware
        # app.add_middleware(
        #     CORSMiddleware,
        #     allow_origins=["*"],
        #     allow_credentials=True,
        #     allow_methods=["*"],
        #     allow_headers=["*"],
        # )

        # 将原应用挂载到指定路径下
        app.mount(path_prefix, agent_app)
        log_info(f"✅ 应用已挂载到路径前缀: {path_prefix}")
    else:
        app = agent_app
        # 当没有路径前缀时，CORS 已在 AgentOS 创建时通过 cors_allowed_origins 参数配置

    # 添加请求日志中间件
    try:
        from middleware.request_logging import RequestLoggingMiddleware  # type: ignore
        app.add_middleware(RequestLoggingMiddleware)
        log_info("✅ 请求日志中间件已启用")
    except ImportError:  # pragma: no cover
        # 如果导入失败，尝试从相对路径导入
        sys.path.append(str(Path(__file__).resolve().parents[1]))
        from middleware.request_logging import RequestLoggingMiddleware  # type: ignore
        app.add_middleware(RequestLoggingMiddleware)
        log_info("✅ 请求日志中间件已启用")

    # 标记为已初始化（使用当前模块对象）
    _module = sys.modules[_module_name]
    setattr(_module, "_agent_os_initialized", True)

    # 服务信息日志（只在第一次初始化时输出）
    from config.config_loader import get_agentos_config
    agentos_config = get_agentos_config()
    log_info("")
    log_info("=" * 80)
    log_info("📋 服务信息")
    log_info("=" * 80)
    port = int(agentos_config.get("port", 14466))
    host = agentos_config.get("host", "0.0.0.0")
    log_info(f"🌐 Web 界面: http://localhost:{port}")
    log_info(f"📚 API 文档: http://localhost:{port}/docs")
    log_info(f"⚙️  配置页面: http://localhost:{port}/config")
    log_info("=" * 80)
    log_info("")
    log_info("💡 提示：")
    log_info("   - 在 Web 界面中可以直接与 Agent 对话")
    log_info("   - 支持流式输出和实时调试")
    log_info("   - 按 Ctrl+C 停止服务")
    log_info("")
else:
    # 如果已经初始化过，直接使用已创建的实例（不输出日志）
    pass
