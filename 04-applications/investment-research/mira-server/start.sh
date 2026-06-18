#!/bin/bash
# Mira API 服务端一键安装 & 启动
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "📦 Mira API Server"
echo "   位置: $SCRIPT_DIR"

# 检查 Python
python3 --version

# 安装依赖（使用清华镜像）
echo ""
echo "📥 安装 Python 依赖..."
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r "$SCRIPT_DIR/requirements.txt"

# 检查 API Key
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  警告: DEEPSEEK_API_KEY 未设置，AI 分析功能将不可用"
    echo "   请先: export DEEPSEEK_API_KEY='sk-...'"
fi

# 启动
echo ""
echo "🚀 启动服务端 (端口 8080)..."
cd "$SCRIPT_DIR"
python3 server.py
