#!/usr/bin/env python3
"""账本园艺 —— 把只追加的记忆账本修剪成能读的东西。

账本（.memory/ledger.jsonl）是真相源，只追加、不改写。
这个工具只读它，产出两样东西：

  1. 重复检测：同一个修复被记了三遍，应该合并成一句
  2. 账本摘要：每个项目一段话（取最近条目），写进 DIGEST.md

用法:
    python3 home/studio/gardener/gardener.py
    python3 home/studio/gardener/gardener.py --write
    python3 home/studio/gardener/gardener.py --threshold 0.5
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / ".memory" / "ledger.jsonl"
DIGEST = Path(__file__).resolve().parent / "DIGEST.md"

TAG_RE = re.compile(r"^【([^】]+)】")
WORD_RE = re.compile(r"[a-z0-9_\-]{3,}")


def load() -> list[dict]:
    entries = []
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def tag_of(text: str) -> str:
    m = TAG_RE.match(text)
    return m.group(1) if m else "未分类"


def tokens(text: str) -> set[str]:
    low = text.lower()
    cjk = [c for c in low if "\u4e00" <= c <= "\u9fff"]
    grams = {"".join(pair) for pair in zip(cjk, cjk[1:])}
    words = set(WORD_RE.findall(low))
    return grams | words


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster(entries: list[dict], threshold: float) -> list[list[int]]:
    """贪心聚类：相似度超过阈值的归为一组。"""
    groups: list[list[int]] = []
    reps: list[set[str]] = []
    for i, e in enumerate(entries):
        toks = tokens(e["text"])
        placed = False
        for gi, rep in enumerate(reps):
            if jaccard(toks, rep) >= threshold:
                groups[gi].append(i)
                placed = True
                break
        if not placed:
            groups.append([i])
            reps.append(toks)
    return [g for g in groups if len(g) > 1]


def fmt_date(ts: str) -> str:
    return ts[:10] if ts else "?"


def clip(text: str, n: int = 160) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.55, help="判为重复的相似度阈值")
    ap.add_argument("--write", action="store_true", help="写入 DIGEST.md")
    args = ap.parse_args()

    entries = load()
    if not entries:
        print("账本为空")
        return 0

    for i, e in enumerate(entries):
        e["_i"] = i
        e["_tag"] = tag_of(e["text"])

    # 按标签分组
    by_tag: dict[str, list[dict]] = {}
    for e in entries:
        by_tag.setdefault(e["_tag"], []).append(e)

    print(f"\n账本共 {len(entries)} 条，{len(by_tag)} 个项目标签\n")
    print(f"{'项目':<28}{'条数':>4}  {'时间跨度':<24}")
    print("-" * 62)
    for tag, items in sorted(by_tag.items(), key=lambda kv: -len(kv[1])):
        dates = sorted(e["ts"] for e in items)
        print(f"{tag:<28}{len(items):>4}  {fmt_date(dates[0])} → {fmt_date(dates[-1])}")

    dup_groups = cluster(entries, args.threshold)
    print(f"\n疑似重复：{len(dup_groups)} 组")
    print("-" * 62)
    for g in dup_groups:
        print(f"· 相似度组（{len(g)} 条）")
        for idx in g:
            e = entries[idx]
            print(f"    [{fmt_date(e['ts'])}] {clip(e['text'], 110)}")

    if args.write:
        lines = ["# 账本摘要", "", "> 由 `home/studio/gardener/gardener.py` 生成，账本本身不改。", ""]
        for tag, items in sorted(by_tag.items(), key=lambda kv: -len(kv[1])):
            items = sorted(items, key=lambda e: e["ts"], reverse=True)
            lines.append(f"## {tag}（{len(items)} 条）")
            lines.append("")
            lines.append(f"最近：{clip(items[0]['text'], 240)}")
            if len(items) > 1:
                lines.append("")
                lines.append(f"更早：{clip(items[1]['text'], 160)}")
            lines.append("")
        DIGEST.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n已写入 {DIGEST.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
