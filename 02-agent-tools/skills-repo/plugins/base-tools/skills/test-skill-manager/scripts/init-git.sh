#!/bin/bash

# Git 初始化脚本
# 用途：为 skill 目录初始化 Git 仓库

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取当前目录
CURRENT_DIR=$(pwd)
SKILL_NAME=$(basename "$CURRENT_DIR")

echo -e "${GREEN}=== Skill Git 初始化 ===${NC}"
echo -e "Skill 目录: ${YELLOW}$CURRENT_DIR${NC}"
echo -e "Skill 名称: ${YELLOW}$SKILL_NAME${NC}"
echo ""

# 检查是否已经是 Git 仓库
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${YELLOW}警告: 当前目录已经是 Git 仓库${NC}"
    git remote -v
    echo ""
    read -p "是否要重新初始化？这将删除现有的 Git 历史 (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}已取消${NC}"
        exit 0
    fi
    rm -rf .git
fi

# 检查 SKILL.md 是否存在
if [ ! -f "SKILL.md" ]; then
    echo -e "${RED}错误: 找不到 SKILL.md 文件${NC}"
    echo "请确保在 skill 目录中运行此脚本"
    exit 1
fi

# 初始化 Git
echo -e "${GREEN}正在初始化 Git 仓库...${NC}"
git init
echo ""

# 创建 .gitignore（如果不存在）
if [ ! -f ".gitignore" ]; then
    echo -e "${GREEN}创建 .gitignore 文件...${NC}"
    cat > .gitignore << 'EOF'
# 临时文件
*.tmp
*.log
*.swp
*~

# 操作系统文件
.DS_Store
Thumbs.db
desktop.ini

# IDE 文件
.vscode/
.idea/
*.iml

# 依赖目录
node_modules/
__pycache__/
*.pyc
EOF
    echo ""
fi

# 添加所有文件
echo -e "${GREEN}添加文件到 Git...${NC}"
git add .
echo ""

# 显示将要提交的文件
echo -e "${YELLOW}将要提交的文件:${NC}"
git status --short
echo ""

# 确认提交
read -p "确认提交这些文件? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${RED}已取消${NC}"
    exit 0
fi

# 创建初始提交
echo -e "${GREEN}创建初始提交...${NC}"
git commit -m "Initial commit: $SKILL_NAME skill"
echo ""

echo -e "${GREEN}✓ Git 仓库初始化成功!${NC}"
echo ""

# 询问是否设置 remote
read -p "是否要设置 remote 仓库? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}请输入 remote 仓库 URL:${NC}"
    echo "示例: git@github.com:username/repo.git"
    echo "      https://github.com/username/repo.git"
    read -p "URL: " REMOTE_URL
    
    if [ -n "$REMOTE_URL" ]; then
        echo ""
        echo -e "${GREEN}添加 remote 'origin'...${NC}"
        git remote add origin "$REMOTE_URL"
        
        echo ""
        echo -e "${GREEN}Remote 添加成功:${NC}"
        git remote -v
        echo ""
        
        # 询问是否推送
        read -p "是否要立即推送到 remote? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo ""
            echo -e "${GREEN}推送到 remote...${NC}"
            
            # 检查并创建 main 分支
            if ! git rev-parse --verify main > /dev/null 2>&1; then
                git branch -M main
            fi
            
            # 推送
            if git push -u origin main; then
                echo ""
                echo -e "${GREEN}✓ 推送成功!${NC}"
            else
                echo ""
                echo -e "${RED}✗ 推送失败${NC}"
                echo "可能的原因:"
                echo "1. remote 仓库不存在"
                echo "2. 没有推送权限"
                echo "3. 网络连接问题"
                echo ""
                echo "请手动推送: git push -u origin main"
            fi
        fi
    fi
fi

echo ""
echo -e "${GREEN}=== 初始化完成 ===${NC}"
echo ""
echo "下一步:"
echo "1. 修改 skill 内容"
echo "2. 提交修改: git add . && git commit -m 'Update: ...'"
echo "3. 推送到 remote: git push"
echo ""
echo "或使用 commit-skill.sh 脚本进行提交"
