#!/usr/bin/env bash
# ============================================================
# 记忆回写的唯一入口。
#
# 为什么需要它：
#   .memory/ 属于父仓库，子模块的 worktree 里没有它，所以任何 Agent
#   回写记忆都只能在主检出里、对着 main 操作。多人/多 Agent 并发时，
#   裸的 add/commit/push 会互相顶掉。
#
# 这个脚本保证：
#   1. 先 rebase 到最新 main
#   2. 只提交 .memory/ledger.jsonl 一个文件
#   3. 推送被拒时自动重试
#   4. ledger 的冲突由 .gitattributes 的 merge=union 自动取并集
#
# 用法:
#   ./scripts/mem-commit.sh "memory: 【项目】做了什么"
# ============================================================
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

MSG="${1:-memory: 记录}"
LEDGER=".memory/ledger.jsonl"

git pull --rebase --autostash origin main

git add "$LEDGER"
if git diff --cached --quiet -- "$LEDGER"; then
  echo "账本无变化，跳过提交"
  exit 0
fi

git commit -m "$MSG" -- "$LEDGER"

for attempt in 1 2 3; do
  if git push origin main; then
    echo "已同步到 main"
    exit 0
  fi
  echo "推送被拒（第 ${attempt} 次），先 rebase 再重试…" >&2
  git pull --rebase --autostash origin main
done

echo "推送仍失败，请手动处理（不要 force push）" >&2
exit 1
