#!/bin/sh

# Agent Skills 目录结构验证脚本
# 在 git push 时自动调用，检查目录结构是否符合规范
# 使用：sh scripts/validate-structure.sh（另起进程执行，不影响当前目录）
# 特点：在子进程中执行，支持在任意目录执行

# 获取脚本所在目录
if [ -n "${BASH_SOURCE[0]}" ]; then
    SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
else
    SCRIPT_PATH="$0"
fi
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 在子 shell 中执行，切换到仓库根目录
(
    cd "$REPO_ROOT"

    ERRORS=""
    ERROR_COUNTS=""

    add_error() {
        type="$1"
        message="$2"
        ERRORS="${ERRORS}[${type}]${message}"$'\n'$'\n'
    }

    count_error() {
        type="$1"
        ERROR_COUNTS="${ERROR_COUNTS}[${type}]"$'\n'
    }

    check_directory_name() {
        dir_path="$1"
        dir_name="$2"
        type="NAMING"

        case "$dir_name" in
            scripts|docs)
                return 0
                ;;
        esac

        case "$dir_name" in
            .*)
                return 0
                ;;
        esac

        case "$dir_name" in
            [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-*)
                return 0
                ;;
        esac

        case "$dir_name" in
            [a-z]*-[a-z0-9]*)
                return 0
                ;;
        esac

        case "$dir_name" in
            [A-Z]*-[A-Z0-9]*)
                return 0
                ;;
        esac

        add_error "$type" "[命名错误] $dir_path"
        add_error "$type" "  → 目录名：'$dir_name'"
        add_error "$type" "  → 允许的格式: kebab-case (如 qa-test) 或 SCREAMING-KEBAB-CASE (如 QA-TEST)"
        add_error "$type" "  → 禁止: 大驼峰、小驼峰、下划线、中文、混写"
        count_error "$type"

        return 1
    }

    check_plugin_directory() {
        plugin_name="$1"

        if [ ! -f "plugins/$plugin_name/README.md" ]; then
            add_error "MISSING_FILE" "[文件缺失] plugins/$plugin_name/README.md"
            add_error "MISSING_FILE" "  → 插件缺少必需的 README.md 文件"
            count_error "MISSING_FILE"
        fi

        if [ ! -d "plugins/$plugin_name/skills" ]; then
            add_error "MISSING_DIR" "[目录缺失] plugins/$plugin_name/skills/"
            add_error "MISSING_DIR" "  → 插件缺少必需的 skills/ 目录"
            count_error "MISSING_DIR"
        fi

        if [ -d "plugins/$plugin_name/skills" ]; then
            skills_count=$(ls -A "plugins/$plugin_name/skills" 2>/dev/null | wc -l)
            skills_count=$(echo "$skills_count" | tr -d ' ')
            if [ "$skills_count" = "0" ]; then
                add_error "EMPTY_DIR" "[目录为空] plugins/$plugin_name/skills/"
                add_error "EMPTY_DIR" "  → skills/ 目录不能为空"
                count_error "EMPTY_DIR"
            fi
        fi

        return 0
    }

    check_skill_directory() {
        plugin_name="$1"
        skill_name="$2"

        if [ ! -f "plugins/$plugin_name/skills/$skill_name/SKILL.md" ]; then
            add_error "MISSING_FILE" "[文件缺失] plugins/$plugin_name/skills/$skill_name/SKILL.md"
            add_error "MISSING_FILE" "  → Skill 缺少必需的 SKILL.md 文件"
            count_error "MISSING_FILE"
        fi

        return 0
    }

    echo "🔍 验证目录结构..."
    echo ""

    if [ ! -d "plugins" ]; then
        echo "❌ 目录结构验证失败"
        echo ""
        echo "  - 缺少 plugins/ 目录"
        echo ""
        echo "请创建 plugins/ 目录后重新提交。"
        exit 1
    fi

    plugins_count=$(ls -A plugins/ 2>/dev/null | wc -l)
    plugins_count=$(echo "$plugins_count" | tr -d ' ')
    if [ "$plugins_count" = "0" ]; then
        echo "❌ 目录结构验证失败"
        echo ""
        echo "  - plugins/ 目录为空，不能为空目录"
        echo ""
        echo "请在 plugins/ 目录下添加插件后重新提交。"
        exit 1
    fi

    for item in plugins/*/; do
        plugin_name=$(basename "$item")
        plugin_path="plugins/$plugin_name"

        dir_path="$(pwd)/$plugin_path"
        check_directory_name "$dir_path" "$plugin_name"

        check_plugin_directory "$plugin_name"

        if [ -d "$plugin_path/skills" ]; then
            for skill_item in "$plugin_path"/skills/*/; do
                skill_name=$(basename "$skill_item")
                skill_path="$plugin_path/$skill_name"
                full_skill_path="$(pwd)/$skill_path"

                check_directory_name "$full_skill_path" "$skill_name"
                check_skill_directory "$plugin_name" "$skill_name"
            done
        fi
    done

    naming_count=0
    if [ -n "$ERROR_COUNTS" ]; then
        naming_count=$(echo "$ERROR_COUNTS" | grep "\[NAMING\]" | wc -l | tr -d ' ')
    fi

    missing_file_count=0
    if [ -n "$ERROR_COUNTS" ]; then
        missing_file_count=$(echo "$ERROR_COUNTS" | grep "\[MISSING_FILE\]" | wc -l | tr -d ' ')
    fi

    missing_dir_count=0
    if [ -n "$ERROR_COUNTS" ]; then
        missing_dir_count=$(echo "$ERROR_COUNTS" | grep "\[MISSING_DIR\]" | wc -l | tr -d ' ')
    fi

    empty_dir_count=0
    if [ -n "$ERROR_COUNTS" ]; then
        empty_dir_count=$(echo "$ERROR_COUNTS" | grep "\[EMPTY_DIR\]" | wc -l | tr -d ' ')
    fi

    total_problems=0
    total_problems=$((naming_count + missing_file_count + missing_dir_count + empty_dir_count))

    if [ "$total_problems" -gt 0 ]; then
        echo "❌ 目录结构验证失败"
        echo ""
        echo "发现 $total_problems 个问题："
        echo ""
        if [ "$naming_count" -gt 0 ]; then
            echo "  • 命名错误 × $naming_count"
        fi
        if [ "$missing_file_count" -gt 0 ]; then
            echo "  • 文件缺失 × $missing_file_count"
        fi
        if [ "$missing_dir_count" -gt 0 ]; then
            echo "  • 目录缺失 × $missing_dir_count"
        fi
        if [ "$empty_dir_count" -gt 0 ]; then
            echo "  • 目录为空 × $empty_dir_count"
        fi
        echo ""
        echo "详细信息："
        echo ""
        echo "$ERRORS"
        echo "请修复以上问题后重新提交。"
        exit 1
    else
        echo "✅ 目录结构验证通过"
        exit 0
    fi
)
