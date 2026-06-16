#!/bin/bash

# Skill 验证脚本
# 用途：验证 skill 的结构和格式是否正确

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

echo -e "${GREEN}=== Skill 验证工具 ===${NC}"
echo -e "Skill 目录: ${YELLOW}$CURRENT_DIR${NC}"
echo -e "Skill 名称: ${YELLOW}$SKILL_NAME${NC}"
echo ""

# 验证计数
ERRORS=0
WARNINGS=0

# 辅助函数
error() {
    echo -e "${RED}✗ $1${NC}"
    ((ERRORS++))
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    ((WARNINGS++))
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

info() {
    echo -e "${BLUE}→ $1${NC}"
}

echo -e "${BLUE}=== 1. 检查必需文件 ===${NC}"

# 检查 SKILL.md 是否存在
if [ ! -f "SKILL.md" ]; then
    error "SKILL.md 文件不存在"
else
    success "SKILL.md 文件存在"
fi

echo ""
echo -e "${BLUE}=== 2. 检查 YAML Frontmatter ===${NC}"

if [ -f "SKILL.md" ]; then
    # 检查 YAML 分隔符
    if ! grep -q "^---$" SKILL.md; then
        error "SKILL.md 缺少 YAML frontmatter 分隔符 (---)"
    else
        success "YAML frontmatter 分隔符存在"
        
        # 提取 YAML frontmatter
        YAML_CONTENT=$(sed -n '/^---$/,/^---$/p' SKILL.md | sed '1d;$d')
        
        # 检查 name 字段
        if echo "$YAML_CONTENT" | grep -q "^name:"; then
            NAME_VALUE=$(echo "$YAML_CONTENT" | grep "^name:" | sed 's/^name: *//' | tr -d '"' | tr -d "'")
            if [ -n "$NAME_VALUE" ]; then
                success "name 字段存在: $NAME_VALUE"
                
                # 检查 name 格式 (kebab-case)
                if ! echo "$NAME_VALUE" | grep -qE "^[a-z0-9]+(-[a-z0-9]+)*$"; then
                    warning "name 应使用 kebab-case 格式 (小写字母、数字、连字符)"
                fi
            else
                error "name 字段为空"
            fi
        else
            error "name 字段不存在"
        fi
        
        # 检查 description 字段
        if echo "$YAML_CONTENT" | grep -q "^description:"; then
            DESC_VALUE=$(echo "$YAML_CONTENT" | grep "^description:" | sed 's/^description: *//')
            if [ -n "$DESC_VALUE" ]; then
                success "description 字段存在"
                
                # 检查 description 格式
                if ! echo "$DESC_VALUE" | grep -qi "This skill should be used when"; then
                    warning "description 建议使用第三人称: 'This skill should be used when...'"
                fi
                
                # 检查是否包含触发短语
                if ! echo "$DESC_VALUE" | grep -q '"'; then
                    warning "description 建议包含具体的触发短语 (用引号包裹)"
                fi
            else
                error "description 字段为空"
            fi
        else
            error "description 字段不存在"
        fi
        
        # 检查 version 字段（可选）
        if echo "$YAML_CONTENT" | grep -q "^version:"; then
            VERSION_VALUE=$(echo "$YAML_CONTENT" | grep "^version:" | sed 's/^version: *//' | tr -d '"' | tr -d "'")
            success "version 字段存在: $VERSION_VALUE"
            
            # 检查版本号格式
            if ! echo "$VERSION_VALUE" | grep -qE "^[0-9]+\.[0-9]+\.[0-9]+$"; then
                warning "version 建议使用语义化版本号 (如 1.0.0)"
            fi
        else
            info "version 字段不存在 (可选)"
        fi
    fi
fi

echo ""
echo -e "${BLUE}=== 3. 检查内容质量 ===${NC}"

if [ -f "SKILL.md" ]; then
    # 跳过 YAML frontmatter 后的内容
    CONTENT=$(sed '1,/^---$/d; /^---$/d' SKILL.md)
    
    # 检查内容长度
    WORD_COUNT=$(echo "$CONTENT" | wc -w | tr -d ' ')
    if [ "$WORD_COUNT" -lt 100 ]; then
        warning "SKILL.md 内容较少 ($WORD_COUNT 字)，建议至少 500 字"
    elif [ "$WORD_COUNT" -gt 5000 ]; then
        warning "SKILL.md 内容较多 ($WORD_COUNT 字)，建议不超过 2000 字，详细内容放入 references/"
    else
        success "SKILL.md 内容长度适中 ($WORD_COUNT 字)"
    fi
    
    # 检查是否有标题
    if ! echo "$CONTENT" | grep -q "^#"; then
        warning "SKILL.md 建议包含标题 (# 开头)"
    else
        success "SKILL.md 包含标题"
    fi
fi

echo ""
echo -e "${BLUE}=== 4. 检查支持文件引用 ===${NC}"

if [ -f "SKILL.md" ]; then
    # 检查是否引用了 references/
    if [ -d "references" ]; then
        if grep -q "references/" SKILL.md; then
            success "SKILL.md 中引用了 references/ 目录"
        else
            warning "存在 references/ 目录但 SKILL.md 中未引用"
        fi
    fi
    
    # 检查是否引用了 examples/
    if [ -d "examples" ]; then
        if grep -q "examples/" SKILL.md; then
            success "SKILL.md 中引用了 examples/ 目录"
        else
            warning "存在 examples/ 目录但 SKILL.md 中未引用"
        fi
    fi
    
    # 检查是否引用了 scripts/
    if [ -d "scripts" ]; then
        if grep -q "scripts/" SKILL.md; then
            success "SKILL.md 中引用了 scripts/ 目录"
        else
            warning "存在 scripts/ 目录但 SKILL.md 中未引用"
        fi
    fi
fi

echo ""
echo -e "${BLUE}=== 5. 检查目录结构 ===${NC}"

# 列出目录结构
if command -v tree &> /dev/null; then
    tree -L 2 -I 'node_modules|__pycache__|.git'
else
    find . -maxdepth 2 -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' | sort
fi

echo ""
echo -e "${BLUE}=== 6. 检查脚本权限 ===${NC}"

if [ -d "scripts" ]; then
    SCRIPT_COUNT=0
    EXECUTABLE_COUNT=0
    
    for script in scripts/*; do
        if [ -f "$script" ]; then
            ((SCRIPT_COUNT++))
            if [ -x "$script" ]; then
                ((EXECUTABLE_COUNT++))
                success "$(basename "$script") 有执行权限"
            else
                warning "$(basename "$script") 没有执行权限，运行: chmod +x $script"
            fi
        fi
    done
    
    if [ $SCRIPT_COUNT -eq 0 ]; then
        info "scripts/ 目录为空"
    fi
else
    info "scripts/ 目录不存在 (可选)"
fi

echo ""
echo -e "${BLUE}=== 7. Git 状态检查 ===${NC}"

if git rev-parse --git-dir > /dev/null 2>&1; then
    success "当前目录是 Git 仓库"
    
    # 检查是否有未提交的修改
    if ! git diff --quiet || ! git diff --cached --quiet; then
        warning "存在未提交的修改"
        git status --short
    else
        success "没有未提交的修改"
    fi
    
    # 检查是否有 remote
    if git remote | grep -q 'origin'; then
        success "已配置 remote 'origin'"
        git remote -v
    else
        info "未配置 remote 仓库 (可选)"
    fi
else
    info "当前目录不是 Git 仓库 (可选)"
fi

# 总结
echo ""
echo -e "${GREEN}=== 验证总结 ===${NC}"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 验证通过！Skill 结构完整且符合规范。${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ 验证通过，但有 $WARNINGS 个警告${NC}"
    echo "建议修复警告以提高 skill 质量"
    exit 0
else
    echo -e "${RED}✗ 验证失败：$ERRORS 个错误，$WARNINGS 个警告${NC}"
    echo "请修复错误后重新验证"
    exit 1
fi
