#!/bin/bash

# ==========================================
# AI 自动装修助手 - CORS 测试脚本（Linux/macOS 版本）
# ==========================================
# 用途：验证跨域请求和 Authorization 头支持
# 环境：Linux / macOS / Git Bash
# ==========================================

BASE_URL="https://ai-gateway-show.yunzhonghe.com/ecom_reco_agent"
ORIGIN="http://localhost:3000"
AUTH_HEADER="Authorization: Bearer test-token-123"

echo ""
echo "========================================="
echo "AI 自动装修助手 - CORS 测试"
echo "========================================="
echo ""
echo "测试环境：$BASE_URL"
echo "来源地址：$ORIGIN"
echo ""

echo "========================================="
echo "1️⃣  测试 OPTIONS 预检请求（带 Authorization）"
echo "========================================="
echo ""
echo "检查浏览器是否能发送带 Authorization 头的跨域请求..."
echo ""
curl -i -X OPTIONS \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  "$BASE_URL/agents/ecom-reco-agent/runs"

echo ""
echo ""
echo "========================================="
echo "2️⃣  测试健康检查接口（GET + Authorization）"
echo "========================================="
echo ""
echo "检查带 Authorization 头的 GET 请求是否正常..."
echo ""
curl -i \
  -H "Origin: $ORIGIN" \
  -H "$AUTH_HEADER" \
  "$BASE_URL/health"

echo ""
echo ""
echo "========================================="
echo "✅ 测试完成"
echo "========================================="
echo ""
echo "验证要点："
echo "1. OPTIONS 请求应返回 204/200，包含 CORS 头"
echo "2. 健康检查应返回 200，包含 CORS 头"
echo "3. 响应头应包含："
echo "   - Access-Control-Allow-Origin: *"
echo "   - Access-Control-Allow-Headers: authorization, content-type"
echo "   - Access-Control-Allow-Methods: POST, GET, OPTIONS"
echo "   - Access-Control-Allow-Credentials: true"
echo ""
