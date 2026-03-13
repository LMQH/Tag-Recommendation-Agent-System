"""
AI自动装修助手 - 启动脚本
提供 Web 界面用于本地调试

启动方式：
    python start.py

访问地址：
    - Web 界面: http://localhost:14466
    - API 文档: http://localhost:14466/docs
    - 配置页面: http://localhost:14466/config
"""

import sys
import warnings
from pathlib import Path
import uvicorn

# 忽略 httpx 客户端销毁时的 AttributeError 警告（openai 1.85.0 与 httpx 0.27.x 兼容性问题）
warnings.filterwarnings("ignore", message=".*SyncHttpxClientWrapper.*")

# 添加 ecom_reco_agent 目录到路径
ecom_reco_dir = Path(__file__).resolve().parent / "ecom_reco_agent"
sys.path.insert(0, str(ecom_reco_dir))

# 导入 agent 模块（这会触发初始化）
from agent.agent_os import agent_os, app  # type: ignore

# 导入配置加载器（在路径设置后）
from config.config_loader import get_agentos_config  # type: ignore


def main():
    """主函数 - 启动 AgentOS 服务"""
    agentos_config = get_agentos_config()
    port = int(agentos_config.get("port", 14466))
    host = agentos_config.get("host", "0.0.0.0")

    try:
        access_log = agentos_config.get("access_log_console", True)
        uvicorn.run(
            app,  # 直接使用 FastAPI app 对象
            host=host,
            port=port,
            reload=False,
            access_log=access_log,
        )
    except KeyboardInterrupt:
        print("\n收到键盘中断信号，正在停止服务...")
    except OSError as e:
        if "address already in use" in str(e):
            print(f"❌ 端口 {port} 已被占用")
            print("💡 解决方案：")
            print("   1. 等待端口释放后重试")
            print(f"   2. 使用其他端口：AGENTOS_PORT=8888 python start.py")
            print(f"   3. 查找并停止占用端口的进程：lsof -i :{port}")
        else:
            print(f"❌ 服务启动失败: {e}")
        raise
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        raise


if __name__ == "__main__":
    main()
