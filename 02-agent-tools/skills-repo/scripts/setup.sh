#!/bin/bash

# Agent Skills 环境验证脚本
# 功能：检测环境配置并执行必要设置
# 使用：source scripts/setup.sh
# 特点：支持在任意目录执行，执行后仍留在当前目录

# 保存当前目录
ORIGINAL_DIR="$(pwd)"

# 获取仓库根目录（支持任意目录执行）
if [[ -n "${BASH_SOURCE[0]}" ]]; then
    SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
else
    SCRIPT_PATH="$0"
fi
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到仓库根目录执行
cd "$REPO_ROOT"

ERRORS=()

echo "========================================"
echo "🔧 Agent Skills 环境验证"
echo "========================================"
echo ""

echo "📋 正在检查 Git Hook 配置..."

HOOKS_PATH=$(git config core.hooksPath 2>/dev/null || echo "")

if [[ "$HOOKS_PATH" == ".githooks" ]]; then
    echo "✅ Git Hook 已正确配置"
    echo ""
    echo "========================================"
    echo "✨ 验证完成，环境就绪！"
    echo "========================================"
    echo ""
    echo "现在您可以："
    echo "  - 使用 AI 探索仓库"
    echo "  - 贡献新的 Skill"
    echo ""
    echo "每次 push 时会自动检查目录结构。"
    cd "$ORIGINAL_DIR"
    return 0
fi

echo "⚠️  Git Hook 未配置，开始自动配置..."
echo ""

echo "📝 正在配置 Git Hook 路径..."
if ! git config core.hooksPath .githooks 2>/dev/null; then
    ERRORS+=("无法设置 Git Hook 路径，请检查 Git 配置权限")
fi

echo "✅ Git Hook 路径已配置"

echo ""
echo "🔐 正在设置脚本执行权限..."
if ! chmod +x .githooks/pre-push 2>/dev/null; then
    ERRORS+=("无法设置 .githooks/pre-push 执行权限")
fi
if ! chmod +x scripts/validate-structure.sh 2>/dev/null; then
    ERRORS+=("无法设置 scripts/validate-structure.sh 执行权限")
fi
echo "✅ 脚本权限已设置"

echo ""
echo "🔍 正在验证配置..."
VERIFIED=$(git config core.hooksPath 2>/dev/null || echo "")
if [[ "$VERIFIED" != ".githooks" ]]; then
    ERRORS+=("配置验证失败：Git Hook 路径未正确设置为 .githooks")
fi
echo "✅ 配置验证成功"

if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo ""
    echo "========================================"
    echo "❌ 设置失败"
    echo "========================================"
    echo ""
    for error in "${ERRORS[@]}"; do
        echo "  - $error"
    done
    echo ""
    echo "请检查错误原因后重试，或联系维护者处理。"
    cd "$ORIGINAL_DIR"
    return 1
fi

echo ""
echo "========================================"
echo "✨ 验证完成，环境就绪！"
echo "========================================"
echo ""
echo "现在您可以："
echo "  - 使用 AI 探索仓库"
echo "  - 贡献新的 Skill"
echo ""
echo "每次 push 时会自动检查目录结构。"

# 恢复原始目录
cd "$ORIGINAL_DIR"
