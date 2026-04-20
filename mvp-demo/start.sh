#!/bin/bash

# 本地生活 AI Skill 平台 - MVP Demo 启动脚本

echo "=========================================="
echo "  本地生活 AI Skill 平台 - MVP Demo"
echo "=========================================="
echo ""

# 启动 Skill Registry
echo "📡 启动 Skill Registry..."
cd "$(dirname "$0")/registry" && npm start &
REGISTRY_PID=$!
sleep 1

# 启动各商家 MCP Server
echo "🍜 启动金谷园饺子馆 MCP Server (8001)..."
cd "$(dirname "$0")/skills/jin-gu-yuan-dumpling" && node server.js &

echo "🍲 启动宏缘火锅 MCP Server (8002)..."
cd "$(dirname "$0")/skills/hong-yuan-hotpot" && node server.js &

echo "🍜 启动季多西面馆 MCP Server (8003)..."
cd "$(dirname "$0")/skills/ji-dong-xi-noodles" && node server.js &

echo "🍳 启动兴华家常菜 MCP Server (8004)..."
cd "$(dirname "$0")/skills/xing-hua-restaurant" && node server.js &

echo ""
echo "=========================================="
echo "  全部服务已启动！"
echo "=========================================="
echo ""
echo "🌐 Skill Registry: http://localhost:3000"
echo "📡 API 端点:"
echo "   - GET  http://localhost:3000/api/skills"
echo "   - GET  http://localhost:3000/api/skills?capabilities=queue"
echo "   - GET  http://localhost:3000/api/skills/search/饺子"
echo ""
echo "🍜 商家 MCP Servers:"
echo "   - 金谷园饺子馆: http://localhost:8001"
echo "   - 宏缘火锅:     http://localhost:8002"
echo "   - 季多西面馆:   http://localhost:8003"
echo "   - 兴华家常菜:   http://localhost:8004"
echo ""

# 等待所有后台进程
wait
