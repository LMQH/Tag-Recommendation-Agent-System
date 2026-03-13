#!/bin/bash
# AI自动装修助手 - 停止脚本
# 用途：停止AgentOS Web服务

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录（bin/ 在项目根目录下）
APP_DIR="$(dirname "$SCRIPT_DIR")"
# PID 文件在 ecom_reco_agent/data/ 下
ECOM_DIR="$APP_DIR/ecom_reco_agent"
PID_FILE="$ECOM_DIR/data/app.pid"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "❌ 服务未运行（PID文件不存在）"
    exit 1
fi

# 读取PID
PID=$(cat "$PID_FILE")

# 检查进程是否还在运行
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  进程不存在 (PID: $PID)，清理PID文件"
    rm -f "$PID_FILE"
    exit 0
fi

echo "=" | tee -a "$APP_DIR/data/logs/app.log"
echo "⏹️  停止AI自动装修助手服务" | tee -a "$APP_DIR/data/logs/app.log"
echo "=" | tee -a "$APP_DIR/data/logs/app.log"
echo "📌 PID: $PID" | tee -a "$APP_DIR/data/logs/app.log"
echo "" | tee -a "$APP_DIR/data/logs/app.log"

# 尝试优雅停止（SIGTERM）
kill "$PID" 2>/dev/null

# 等待进程退出（最多5秒）
for i in {1..5}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ 服务已停止" | tee -a "$APP_DIR/data/logs/app.log"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# 如果进程还在运行，强制停止（SIGKILL）
if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  强制停止服务..." | tee -a "$APP_DIR/data/logs/app.log"
    kill -9 "$PID" 2>/dev/null
    sleep 1

    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ 服务已强制停止" | tee -a "$APP_DIR/data/logs/app.log"
        rm -f "$PID_FILE"
        exit 0
    else
        echo "❌ 无法停止服务 (PID: $PID)" | tee -a "$APP_DIR/data/logs/app.log"
        exit 1
    fi
fi
