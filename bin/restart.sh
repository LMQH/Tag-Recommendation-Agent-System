#!/bin/bash
# AI自动装修助手 - 重启脚本
# 用途：先停止再启动 AgentOS Web 服务

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录（bin/ 在项目根目录下）
APP_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔄 重启 AI自动装修助手服务..."
echo ""

# 先停止（若未运行，stop.sh 会提示并 exit 1，这里忽略错误继续尝试启动）
"$SCRIPT_DIR/stop.sh" || true

# 等待进程完全退出
sleep 2

# 再启动
"$SCRIPT_DIR/start.sh"
