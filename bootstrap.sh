#!/usr/bin/env bash
# ============================================================
# ai-instructure 工作区引导脚本
# 目标：在一台新机器上把工作区恢复到"能跑"的状态。
#
#   ./bootstrap.sh            检查环境 + 初始化子模块（不安装依赖）
#   ./bootstrap.sh --install  额外安装各项目的依赖
#   ./bootstrap.sh --check    只检查，不改动任何东西
#
# 脚本不会安装系统级工具（Flutter/Android SDK/Docker 需自行安装）。
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MODE="setup"
case "${1:-}" in
  --check)   MODE="check" ;;
  --install) MODE="install" ;;
  ""|--setup) MODE="setup" ;;
  -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
  *) echo "未知参数: $1"; exit 1 ;;
esac

if [ -t 1 ]; then
  B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'
else
  B=""; G=""; Y=""; R=""; N=""
fi

ok()   { echo "  ${G}✓${N} $*"; }
warn() { echo "  ${Y}!${N} $*"; MISSING+=("$*"); }
bad()  { echo "  ${R}✗${N} $*"; MISSING+=("$*"); }
section() { echo; echo "${B}$*${N}"; }

MISSING=()

# ---------- 1. 基础工具 ----------
section "1/5 基础工具"
for cmd in git python3 node npm; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "$cmd $("$cmd" --version 2>/dev/null | sed -n 1p)"
  else
    bad "$cmd 未安装"
  fi
done

# 可选工具
for cmd in uv flutter java docker pnpm; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "$cmd"
  else
    warn "$cmd 未安装（仅部分项目需要）"
  fi
done

# ---------- 2. 远端与 SSH ----------
section "2/5 Git 远端"
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo '')"
echo "  origin = ${REMOTE_URL:-<未配置>}"
if [[ "$REMOTE_URL" == git@github-momo0205:* ]]; then
  ssh_out="$(ssh -o BatchMode=yes -o ConnectTimeout=8 -T git@github-momo0205 2>&1 || true)"
  if printf '%s' "$ssh_out" | grep -q "successfully authenticated"; then
    ok "SSH 别名 github-momo0205 可用"
  else
    warn "SSH 别名 github-momo0205 不可用（见 projects.yaml 的 manual_setup）"
  fi
fi

# ---------- 3. 子模块 ----------
section "3/5 子模块"
# 注意：本工作区里有两类目录——
#   * 真正的 submodule（.git 是文件，指向 ../.git/modules/...）
#   * 独立克隆（.git 是目录），父仓只记录指针
# 后者已存在时不要跑 submodule update，否则会冲突。
if [ "$MODE" = "check" ]; then
  git submodule status | sed 's/^/  /'
else
  while IFS= read -r path; do
    [ -z "$path" ] && continue
    if [ -e "$path/.git" ]; then
      if [ -f "$path/.git" ]; then
        ok "$path（子模块）"
      else
        ok "$path（独立克隆，跳过）"
      fi
    else
      git submodule update --init --recursive -- "$path" \
        && ok "$path（已拉取）" || warn "$path 拉取失败"
    fi
  done < <(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}')
fi

# ---------- 4. 环境变量 ----------
section "4/5 环境变量"
if [ -f .env ]; then
  ok ".env 已存在"
else
  if [ "$MODE" = "check" ]; then
    warn ".env 不存在（cp .env.example .env 并填 DEEPSEEK_API_KEY）"
  else
    cp .env.example .env
    warn "已生成 .env，请填入 DEEPSEEK_API_KEY"
  fi
fi

# ---------- 5. 项目依赖 ----------
section "5/5 项目依赖"
install_node() {
  local dir="$1"
  if [ -f "$dir/package.json" ]; then
    if [ -d "$dir/node_modules" ]; then
      ok "$dir 依赖已存在"
    elif [ "$MODE" = "install" ]; then
      (cd "$dir" && if [ -f pnpm-lock.yaml ]; then pnpm install; else npm ci; fi) \
        && ok "$dir 依赖已安装" || warn "$dir 依赖安装失败"
    else
      warn "$dir 需要安装依赖（加 --install）"
    fi
  fi
}

install_python() {
  local dir="$1"
  if [ -f "$dir/pyproject.toml" ]; then
    if [ -d "$dir/.venv" ]; then
      ok "$dir .venv 已存在"
    elif [ "$MODE" = "install" ]; then
      if command -v uv >/dev/null 2>&1; then
        (cd "$dir" && uv sync) && ok "$dir 依赖已安装" || warn "$dir uv sync 失败"
      else
        warn "$dir 需要 uv（brew install uv）"
      fi
    else
      warn "$dir 需要创建 .venv（加 --install）"
    fi
  fi
}

install_node   "02-agent-tools/drawio-generator"
install_node   "04-applications/investment-research/finance-ironmao"
install_python "04-applications/investment-research/a-stock-strategy"
install_python "03-research/jev-decision-lab"

# ---------- 收尾 ----------
echo
if [ ${#MISSING[@]} -eq 0 ]; then
  echo "${G}环境检查通过。${N}"
else
  echo "${Y}还有 ${#MISSING[@]} 项待处理：${N}"
  printf '  - %s\n' "${MISSING[@]}"
fi

cat <<'EOF'

还需要你手动做的事（脚本不碰密钥）：
  1. .env 里填 DEEPSEEK_API_KEY      → 记忆系统要靠它做抽取/翻译
  2. Android 项目放置 key.properties → 签名密钥不进 git
  3. 可选：python3 .memory/mem.py rebuild   → 从账本重建记忆索引

常用命令：
  python3 .memory/mem.py search "关键词"
  python3 .memory/mem.py add "【项目】做了什么 / 关键决策 / 踩坑"
EOF
