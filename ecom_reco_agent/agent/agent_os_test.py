"""
AgentOS 纯启动入口（仅通过 AgentOS.get_app() 启动）

与 agent_os.py（手动追加路由）、agent_os_mount.py（挂载模式）区分：
本文件仅创建 AgentOS、调用 get_app() 后直接 uvicorn 启动，无自定义 app、无 path_prefix、无请求日志中间件。

运行方式（项目根目录 ai-automated-renovation 下）：
    python -m ecom_reco_agent.agent.agent_os_test
    python ecom_reco_agent/agent/agent_os_test.py

运行后可在网页端 agentOS 控制面板进行测试
"""

import sys
import warnings
from pathlib import Path

# 确保 ecom_reco_agent 在路径中（本文件在 agent/ 下，故取 parent.parent）
_ecom_reco_root = Path(__file__).resolve().parent.parent
if str(_ecom_reco_root) not in sys.path:
    sys.path.insert(0, str(_ecom_reco_root))

# 忽略 httpx 客户端销毁时的 AttributeError 警告
warnings.filterwarnings("ignore", message=".*SyncHttpxClientWrapper.*")

# 初始化日志（需在导入 agent 前完成）
from config.config_loader import get_logging_config  # type: ignore
from utils.agno_logger import setup_agno_logging_from_config  # type: ignore

logging_config = get_logging_config()
setup_agno_logging_from_config(logging_config)

# 创建 AgentOS 并获取其内置 app（仅通过 AgentOS 启动）
from agent.agent_os import create_agent_os  # type: ignore
from config.config_loader import get_agentos_config  # type: ignore
import uvicorn


def main() -> None:
    agent_os = create_agent_os()
    app = agent_os.get_app()
    agentos_config = get_agentos_config()
    host = agentos_config.get("host", "0.0.0.0")
    port = int(agentos_config.get("port", 14466))

    try:
        access_log = agentos_config.get("access_log_console", True)
        uvicorn.run(app, host=host, port=port, reload=False, access_log=access_log)
    except KeyboardInterrupt:
        print("\n收到键盘中断信号，正在停止服务...")
    except OSError as e:
        if "address already in use" in str(e):
            print(f"端口 {port} 已被占用")
            print(f"可指定其他端口运行")
        else:
            raise
    except Exception as e:
        print(f"服务启动失败: {e}")
        raise


if __name__ == "__main__":
    main()
