#!/bin/bash
# AI自动装修助手 - 状态检查脚本
# 用途：检查AgentOS Web服务运行状态

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录（bin/ 在项目根目录下）
APP_DIR="$(dirname "$SCRIPT_DIR")"
# PID 文件和日志文件在 ecom_reco_agent/data/ 下
ECOM_DIR="$APP_DIR/ecom_reco_agent"
PID_FILE="$ECOM_DIR/data/app.pid"
LOG_FILE="$ECOM_DIR/data/logs/app.log"

echo "=" | tee -a "$LOG_FILE"
echo "📊 AI自动装修助手服务状态" | tee -a "$LOG_FILE"
echo "=" | tee -a "$LOG_FILE"
echo ""

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "❌ 服务未运行（PID文件不存在）" | tee -a "$LOG_FILE"
    echo ""
    echo "💡 启动服务: bin/start.sh"
    exit 1
fi

# 读取PID
PID=$(cat "$PID_FILE")

# 检查进程是否在运行
if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ 服务运行中" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "📌 PID: $PID" | tee -a "$LOG_FILE"
    echo "📁 项目目录: $APP_DIR" | tee -a "$LOG_FILE"
    echo "📄 日志文件: $LOG_FILE" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "💡 查看日志: tail -f $LOG_FILE" | tee -a "$LOG_FILE"
    echo "💡 停止服务: bin/stop.sh" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "🌐 访问地址：" | tee -a "$LOG_FILE"
    echo "   Web 界面: http://localhost:14466" | tee -a "$LOG_FILE"
    echo "   API 文档: http://localhost:14466/docs" | tee -a "$LOG_FILE"
    echo "   配置页面: http://localhost:14466/config" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    # 显示进程资源使用情况
    if command -v ps > /dev/null 2>&1; then
        echo "📊 进程信息：" | tee -a "$LOG_FILE"
        ps -p "$PID" -o pid,ppid,cmd,%mem,%cpu,etime | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
    fi
else
    echo "❌ PID文件存在但进程不存在" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "💡 清理PID文件: rm -f $PID_FILE" | tee -a "$LOG_FILE"
    echo "💡 重新启动: bin/start.sh" | tee -a "$LOG_FILE"
    exit 1
fi
