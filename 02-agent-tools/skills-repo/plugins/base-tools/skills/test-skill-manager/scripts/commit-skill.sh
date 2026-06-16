#!/bin/bash

# Skill 提交脚本
# 用途：提交 skill 的修改并可选推送到 remote

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取当前目录
CURRENT_DIR=$(pwd)
SKILL_NAME=$(basename "$CURRENT_DIR")

echo -e "${GREEN}=== Skill 提交工具 ===${NC}"
echo -e "Skill 目录: ${YELLOW}$CURRENT_DIR${NC}"
echo -e "Skill 名称: ${YELLOW}$SKILL_NAME${NC}"
echo ""

# 检查是否是 Git 仓库
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}错误: 当前目录不是 Git 仓库${NC}"
    echo "请先运行 init-git.sh 初始化 Git"
    exit 1
fi

# 检查是否有修改
if git diff --quiet && git diff --cached --quiet; then
    echo -e "${YELLOW}没有检测到文件修改${NC}"
    exit 0
fi

# 显示修改状态
echo -e "${BLUE}=== 文件修改状态 ===${NC}"
git status --short
echo ""

# 显示详细修改
echo -e "${BLUE}=== 详细修改内容 ===${NC}"
git diff
echo ""
git diff --cached
echo ""

# 询问是否继续
read -p "是否要提交这些修改? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${RED}已取消${NC}"
    exit 0
fi

# 添加文件
echo ""
echo -e "${GREEN}添加修改的文件...${NC}"
git add .
echo ""

# 显示将要提交的文件
echo -e "${YELLOW}将要提交的文件:${NC}"
git status --short
echo ""

# 提示输入 commit 类型
echo -e "${BLUE}=== Commit 消息 ===${NC}"
echo "选择 commit 类型:"
echo "  1) feat     - 新功能"
echo "  2) fix      - 修复 bug"
echo "  3) docs     - 文档变更"
echo "  4) style    - 格式调整（不影响功能）"
echo "  5) refactor - 重构（不是新功能也不是 bug 修复）"
echo "  6) test     - 添加测试"
echo "  7) chore    - 构建或工具变更"
echo "  8) custom   - 自定义消息"
echo ""

read -p "请选择 (1-8): " -n 1 COMMIT_TYPE_CHOICE
echo ""

case $COMMIT_TYPE_CHOICE in
    1) COMMIT_TYPE="feat" ;;
    2) COMMIT_TYPE="fix" ;;
    3) COMMIT_TYPE="docs" ;;
    4) COMMIT_TYPE="style" ;;
    5) COMMIT_TYPE="refactor" ;;
    6) COMMIT_TYPE="test" ;;
    7) COMMIT_TYPE="chore" ;;
    8) COMMIT_TYPE="" ;;
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac

echo ""
if [ -n "$COMMIT_TYPE" ]; then
    read -p "请输入 commit 消息 (简短描述): " COMMIT_MSG
    
    # 询问是否添加详细说明
    read -p "是否添加详细说明? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "请输入详细说明 (输入空行结束):"
        COMMIT_BODY=""
        while IFS= read -r line; do
            [ -z "$line" ] && break
            COMMIT_BODY="${COMMIT_BODY}${line}\n"
        done
        
        # 构建完整的 commit 消息
        FULL_COMMIT_MSG="${COMMIT_TYPE}: ${COMMIT_MSG}"
        if [ -n "$COMMIT_BODY" ]; then
            FULL_COMMIT_MSG="${FULL_COMMIT_MSG}\n\n${COMMIT_BODY}"
        fi
    else
        FULL_COMMIT_MSG="${COMMIT_TYPE}: ${COMMIT_MSG}"
    fi
else
    # 自定义消息
    read -p "请输入完整的 commit 消息: " FULL_COMMIT_MSG
fi

# 显示 commit 消息
echo ""
echo -e "${YELLOW}Commit 消息:${NC}"
echo -e "$FULL_COMMIT_MSG"
echo ""

# 确认提交
read -p "确认提交? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${RED}已取消${NC}"
    exit 0
fi

# 执行提交
echo ""
echo -e "${GREEN}正在提交...${NC}"
echo -e "$FULL_COMMIT_MSG" | git commit -F -
echo ""

echo -e "${GREEN}✓ 提交成功!${NC}"
echo ""

# 显示提交历史
echo -e "${BLUE}最近的提交:${NC}"
git log --oneline -5
echo ""

# 检查是否有 remote
if git remote | grep -q 'origin'; then
    echo -e "${YELLOW}检测到 remote 'origin'${NC}"
    git remote -v
    echo ""
    
    # 询问是否推送
    read -p "是否要推送到 remote? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo ""
        echo -e "${GREEN}正在推送...${NC}"
        
        # 获取当前分支
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
        
        # 推送
        if git push origin "$CURRENT_BRANCH"; then
            echo ""
            echo -e "${GREEN}✓ 推送成功!${NC}"
        else
            echo ""
            echo -e "${RED}✗ 推送失败${NC}"
            echo "请手动推送: git push origin $CURRENT_BRANCH"
        fi
    fi
else
    echo -e "${YELLOW}未检测到 remote 仓库${NC}"
    echo "如需推送到远程，请先设置 remote:"
    echo "  git remote add origin <url>"
    echo "  git push -u origin main"
fi

echo ""
echo -e "${GREEN}=== 提交完成 ===${NC}"
