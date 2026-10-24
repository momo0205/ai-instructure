#!/usr/bin/env bash
# ============================================================
# 把 05-mobile/*.apk 发布到 GitHub Releases。
#
# 为什么需要它：APK 已从 git 排除（它们让仓库历史膨胀到 145MB），
# 但手机上安装仍然需要一个可下载的地址——Releases 就是那个地方。
#
# 用法（在你自己的终端里跑，需要 gh 已登录）：
#   ./scripts/publish-apk.sh                 # tag 默认为 apk-YYYYMMDD
#   ./scripts/publish-apk.sh apk-1.2.0       # 指定 tag
# ============================================================
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

TAG="${1:-apk-$(date +%Y%m%d)}"

if ! command -v gh >/dev/null 2>&1; then
  echo "需要 gh CLI：brew install gh && gh auth login" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "gh 未登录，先执行：gh auth login" >&2
  exit 1
fi

shopt -s nullglob
FILES=(05-mobile/*.apk)
shopt -u nullglob

if [ ${#FILES[@]} -eq 0 ]; then
  echo "05-mobile/ 下没有 .apk 文件" >&2
  exit 1
fi

if gh release view "$TAG" >/dev/null 2>&1; then
  echo "Release $TAG 已存在，换个 tag 或先删除" >&2
  exit 1
fi

echo "将发布 ${#FILES[@]} 个文件到 Release: $TAG"
printf '  %s\n' "${FILES[@]}"

gh release create "$TAG" "${FILES[@]}" \
  --title "$TAG" \
  --notes "Mira 客户端安装包（$(date +%Y-%m-%d)）"

echo "完成。下载地址见：gh release view $TAG"
