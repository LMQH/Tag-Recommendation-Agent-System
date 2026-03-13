#!/bin/bash
# AI自动装修助手 - 启动脚本
# 用途：后台启动AgentOS Web服务

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录（bin/ 在项目根目录下）
APP_DIR="$(dirname "$SCRIPT_DIR")"
# PID 文件和日志文件在 ecom_reco_agent/data/ 下
ECOM_DIR="$APP_DIR/ecom_reco_agent"
PID_FILE="$ECOM_DIR/data/app.pid"
LOG_FILE="$ECOM_DIR/data/logs/app.log"

# 创建必要的目录
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$PID_FILE")"

# 检查PID文件是否存在
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    # 检查进程是否还在运行
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "❌ 服务已在运行 (PID: $PID)"
        echo "💡 如需重启，请先运行: bin/stop.sh"
        exit 1
    else
        echo "⚠️  PID文件存在但进程不存在，清理旧PID文件"
        rm -f "$PID_FILE"
    fi
fi

# 进入项目目录
cd "$APP_DIR" || exit 1

echo "=" | tee -a "$LOG_FILE"
echo "🚀 启动AI自动装修助手服务" | tee -a "$LOG_FILE"
echo "=" | tee -a "$LOG_FILE"
echo "📁 项目目录: $APP_DIR" | tee -a "$LOG_FILE"
echo "📝 日志文件: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 启动服务（后台运行）
nohup python start.py >> "$LOG_FILE" 2>&1 &
PID=$!

# 保存PID
echo $PID > "$PID_FILE"

# 等待几秒检查服务是否启动成功
sleep 3

# 检查进程是否还在运行
if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ 服务已成功启动" | tee -a "$LOG_FILE"
    echo "📌 PID: $PID" | tee -a "$LOG_FILE"
    echo "📄 日志: tail -f $LOG_FILE"
    echo ""
    echo "💡 访问地址："
    echo "   🌐 Web 界面: http://localhost:14466"
    echo "   📚 API 文档: http://localhost:14466/docs"
    echo "   ⚙️  配置页面: http://localhost:14466/config"
    echo ""
    echo "🛠️  管理命令："
    echo "   查看状态: bin/status.sh"
    echo "   停止服务: bin/stop.sh"
    echo "   查看日志: tail -f $LOG_FILE"
else
    echo "❌ 服务启动失败，请查看日志: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
