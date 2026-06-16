#!/bin/bash
# shellcheck disable=SC2059

# Agent Skills 管理脚本
# 功能：将当前项目中的 skill 复制到 ~/.kwaipilot/skills 目录，或从该目录删除同名 skill
# 使用：
#   安装：sh scripts/manage-skills.sh install [skill-name]
#   卸载：sh scripts/manage-skills.sh uninstall [skill-name]
#   列表：sh scripts/manage-skills.sh list
# 特点：支持在任意目录执行，通过查找 SKILL.md 文件定位 skill 目录

set -e

# 获取脚本所在目录
if [[ -n "${BASH_SOURCE[0]}" ]]; then
    SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
else
    SCRIPT_PATH="$0"
fi
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 目标目录
TARGET_DIR="$HOME/.kwaipilot/skills"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印帮助信息
print_help() {
    echo "========================================"
    echo "🔧 Agent Skills 管理工具"
    echo "========================================"
    echo ""
    echo "用法："
    echo "  sh scripts/manage-skills.sh <command> [options]"
    echo ""
    echo "命令："
    echo "  install [skill]     安装 skill 到 ~/.kwaipilot/skills"
    echo "  uninstall [skill]   从 ~/.kwaipilot/skills 卸载 skill"
    echo "  list                列出所有可用的 skill"
    echo "  status              显示已安装的 skill 状态"
    echo "  help                显示此帮助信息"
    echo ""
    echo "选项："
    echo "  --all               操作所有 skill（与 install/uninstall 配合使用）"
    echo ""
    echo "示例："
    echo "  sh scripts/manage-skills.sh list"
    echo "  sh scripts/manage-skills.sh install commit-msg"
    echo "  sh scripts/manage-skills.sh install --all"
    echo "  sh scripts/manage-skills.sh uninstall test-case-generate"
    echo "  sh scripts/manage-skills.sh uninstall --all"
    echo "  sh scripts/manage-skills.sh status"
    echo ""
}

# 查找所有包含 SKILL.md 的目录
# 返回格式: skill_name|source_dir（每行一个）
find_all_skills() {
    cd "$REPO_ROOT"
    
    # 查找所有 SKILL.md 文件，获取其父目录
    find plugins -name "SKILL.md" -type f 2>/dev/null | while read -r skill_file; do
        skill_dir=$(dirname "$skill_file")
        skill_name=$(basename "$skill_dir")
        echo "$skill_name|$REPO_ROOT/$skill_dir"
    done
}

# 根据 skill 名查找源目录
find_skill_source() {
    skill_name="$1"
    cd "$REPO_ROOT"
    
    # 查找包含 SKILL.md 的目录，目录名与 skill_name 匹配
    find plugins -name "SKILL.md" -type f 2>/dev/null | while read -r skill_file; do
        skill_dir=$(dirname "$skill_file")
        dir_name=$(basename "$skill_dir")
        if [ "$dir_name" = "$skill_name" ]; then
            echo "$REPO_ROOT/$skill_dir"
            return 0
        fi
    done
}

# 列出所有可用的 skill
list_skills() {
    echo "========================================"
    echo "📋 可用的 Skills"
    echo "========================================"
    echo ""
    
    cd "$REPO_ROOT"
    
    if [ ! -d "plugins" ]; then
        printf "${RED}❌ 未找到 plugins 目录${NC}\n"
        exit 1
    fi
    
    skill_count=0
    find_all_skills | while IFS='|' read -r skill_name source_dir; do
        if [ -n "$skill_name" ]; then
            skill_count=$((skill_count + 1))
            
            # 获取相对路径用于显示
            rel_path="${source_dir#$REPO_ROOT/}"
            
            # 检查是否已安装
            if [ -d "$TARGET_DIR/$skill_name" ]; then
                printf "  ${GREEN}✓${NC} %s ${GREEN}(已安装)${NC}\n" "$skill_name"
                printf "    ${BLUE}→${NC} %s\n" "$rel_path"
            else
                printf "  ${BLUE}○${NC} %s\n" "$skill_name"
                printf "    ${BLUE}→${NC} %s\n" "$rel_path"
            fi
        fi
    done
    
    # 统计数量
    total=$(find_all_skills | wc -l | tr -d ' ')
    echo ""
    echo "共 $total 个 skill"
    echo ""
}

# 显示已安装状态
show_status() {
    echo "========================================"
    echo "📊 已安装的 Skills 状态"
    echo "========================================"
    echo ""
    
    if [ ! -d "$TARGET_DIR" ]; then
        echo "目标目录 $TARGET_DIR 不存在"
        echo "尚未安装任何 skill"
        echo ""
        return
    fi
    
    installed_count=0
    for skill_dir in "$TARGET_DIR"/*/; do
        if [ -d "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ]; then
            skill_name=$(basename "$skill_dir")
            installed_count=$((installed_count + 1))
            printf "  ${GREEN}✓${NC} %s\n" "$skill_name"
        fi
    done
    
    if [ "$installed_count" -eq 0 ]; then
        echo "尚未安装任何 skill"
    else
        echo ""
        echo "共安装 $installed_count 个 skill"
    fi
    echo ""
    echo "安装目录：$TARGET_DIR"
    echo ""
}

# 安装单个 skill
install_skill() {
    skill_name="$1"
    
    # 查找源目录
    source_dir=$(find_skill_source "$skill_name")
    
    if [ -z "$source_dir" ] || [ ! -d "$source_dir" ]; then
        printf "${RED}❌ 未找到 skill: %s${NC}\n" "$skill_name"
        echo "   提示：请确保该 skill 目录下包含 SKILL.md 文件"
        return 1
    fi
    
    target_dir="$TARGET_DIR/$skill_name"
    
    # 创建目标目录
    mkdir -p "$TARGET_DIR"
    
    # 如果目标已存在，先删除
    if [ -d "$target_dir" ]; then
        rm -rf "$target_dir"
    fi
    
    # 复制 skill 目录
    cp -r "$source_dir" "$target_dir"
    
    printf "${GREEN}✓${NC} 已安装: %s\n" "$skill_name"
    printf "  ${BLUE}→${NC} %s\n" "$target_dir"
}

# 卸载单个 skill
uninstall_skill() {
    skill_name="$1"
    
    target_dir="$TARGET_DIR/$skill_name"
    
    # 检查目标是否存在
    if [ ! -d "$target_dir" ]; then
        printf "${YELLOW}⚠${NC} 未安装: %s\n" "$skill_name"
        return 0
    fi
    
    # 删除 skill
    rm -rf "$target_dir"
    
    printf "${GREEN}✓${NC} 已卸载: %s\n" "$skill_name"
}

# 安装所有 skill
install_all() {
    echo "========================================"
    echo "📦 安装所有 Skills"
    echo "========================================"
    echo ""
    
    cd "$REPO_ROOT"
    
    if [ ! -d "plugins" ]; then
        printf "${RED}❌ 未找到 plugins 目录${NC}\n"
        exit 1
    fi
    
    # 创建目标目录
    mkdir -p "$TARGET_DIR"
    
    install_count=0
    find_all_skills | while IFS='|' read -r skill_name source_dir; do
        if [ -n "$skill_name" ] && [ -d "$source_dir" ]; then
            target_dir="$TARGET_DIR/$skill_name"
            
            # 如果目标已存在，先删除
            if [ -d "$target_dir" ]; then
                rm -rf "$target_dir"
            fi
            
            # 复制 skill 目录
            cp -r "$source_dir" "$target_dir"
            
            printf "${GREEN}✓${NC} 已安装: %s\n" "$skill_name"
            install_count=$((install_count + 1))
        fi
    done
    
    # 统计数量
    total=$(find_all_skills | wc -l | tr -d ' ')
    
    echo ""
    echo "========================================"
    printf "${GREEN}✨ 安装完成！共安装 %d 个 skill${NC}\n" "$total"
    echo "========================================"
    echo ""
    echo "安装目录：$TARGET_DIR"
    echo ""
}

# 卸载所有 skill
uninstall_all() {
    echo "========================================"
    echo "🗑️  卸载所有 Skills"
    echo "========================================"
    echo ""
    
    cd "$REPO_ROOT"
    
    if [ ! -d "plugins" ]; then
        printf "${RED}❌ 未找到 plugins 目录${NC}\n"
        exit 1
    fi
    
    uninstall_count=0
    find_all_skills | while IFS='|' read -r skill_name source_dir; do
        if [ -n "$skill_name" ]; then
            target_dir="$TARGET_DIR/$skill_name"
            
            if [ -d "$target_dir" ]; then
                rm -rf "$target_dir"
                printf "${GREEN}✓${NC} 已卸载: %s\n" "$skill_name"
                uninstall_count=$((uninstall_count + 1))
            fi
        fi
    done
    
    # 检查是否有卸载
    total_installed=0
    find_all_skills | while IFS='|' read -r skill_name source_dir; do
        if [ -n "$skill_name" ] && [ -d "$TARGET_DIR/$skill_name" ]; then
            total_installed=$((total_installed + 1))
        fi
    done
    
    echo ""
    echo "========================================"
    printf "${GREEN}✨ 卸载完成！${NC}\n"
    echo "========================================"
    echo ""
}

# 主逻辑
main() {
    command="${1:-help}"
    
    case "$command" in
        install)
            if [ "$2" = "--all" ]; then
                install_all
            elif [ -n "$2" ]; then
                echo "========================================"
                echo "📦 安装 Skill"
                echo "========================================"
                echo ""
                mkdir -p "$TARGET_DIR"
                install_skill "$2"
                echo ""
            else
                printf "${RED}❌ 错误：请指定 skill 名，或使用 --all${NC}\n"
                echo ""
                echo "用法："
                echo "  sh scripts/manage-skills.sh install <skill-name>"
                echo "  sh scripts/manage-skills.sh install --all"
                exit 1
            fi
            ;;
        uninstall)
            if [ "$2" = "--all" ]; then
                uninstall_all
            elif [ -n "$2" ]; then
                echo "========================================"
                echo "🗑️  卸载 Skill"
                echo "========================================"
                echo ""
                uninstall_skill "$2"
                echo ""
            else
                printf "${RED}❌ 错误：请指定 skill 名，或使用 --all${NC}\n"
                echo ""
                echo "用法："
                echo "  sh scripts/manage-skills.sh uninstall <skill-name>"
                echo "  sh scripts/manage-skills.sh uninstall --all"
                exit 1
            fi
            ;;
        list)
            list_skills
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            print_help
            ;;
        *)
            printf "${RED}❌ 未知命令: %s${NC}\n" "$command"
            echo ""
            print_help
            exit 1
            ;;
    esac
}

main "$@"
