#!/usr/bin/env python3
"""工作区脉搏 —— 一眼看清每个项目的状态。

用法:
    python3 home/studio/pulse/pulse.py
    python3 home/studio/pulse/pulse.py --stale 14
    python3 home/studio/pulse/pulse.py --all
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def git(path: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True, text=True, timeout=15,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def load_projects() -> dict:
    try:
        import yaml
    except ImportError:
        sys.exit("需要 pyyaml：pip3 install pyyaml")
    with open(ROOT / "projects.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stale", type=int, default=30, help="超过多少天算停滞")
    ap.add_argument("--all", action="store_true", help="显示 reference/archived")
    args = ap.parse_args()

    data = load_projects()
    today = dt.date.today()
    rows = []

    for p in data["projects"]:
        path = ROOT / p["path"]
        exists = path.is_dir() and any(path.iterdir()) if path.exists() else False

        last_date, subject, dirty = "", "", 0
        if exists and (path / ".git").exists():
            # 子模块 / 独立仓库：看自己的历史
            raw = git(path, "log", "-1", "--format=%cs|%s", "--", ".", ":(exclude)*.md")
            if "|" in raw:
                last_date, subject = raw.split("|", 1)
            dirty = len(git(path, "status", "--porcelain").splitlines())
        elif exists:
            # 直接跟踪在父仓里的项目：看父仓中触及该路径的最近一次提交
            raw = git(ROOT, "log", "-1", "--format=%cs|%s", "--", p["path"], ":(exclude)*.md")
            if "|" in raw:
                last_date, subject = raw.split("|", 1)
            dirty = len(git(ROOT, "status", "--porcelain", "--", p["path"]).splitlines())

        if last_date:
            age = (today - dt.date.fromisoformat(last_date)).days
        else:
            age = None

        rows.append({
            "id": p["id"], "kind": p["kind"], "state": p.get("state", "?"),
            "exists": exists, "age": age, "dirty": dirty,
        })

    # 未拉取的排最前，其余按「最久没动」排
    rows.sort(key=lambda r: (r["exists"], -(r["age"] if r["age"] is not None else 99999)))

    print(f"\n工作区脉搏 · {today} · {len(rows)} 个项目\n")
    print(f"{'项目':<26}{'类型':<11}{'状态':<12}{'最后代码提交':<12}{'未提交':>6}")
    print("-" * 74)

    shown = 0
    for r in rows:
        if not args.all and r["state"] in {"reference", "archived"}:
            continue
        shown += 1
        if not r["exists"]:
            print(f"{r['id']:<26}{r['kind']:<11}{r['state']:<12}{'未拉取':<12}{'-':>6}")
            continue
        age = f"{r['age']} 天前" if r["age"] is not None else "无提交"
        mark = ""
        if r["age"] is not None and r["age"] > args.stale:
            mark += " ⏳"
        if r["dirty"]:
            mark += " ●"
        print(f"{r['id']:<26}{r['kind']:<11}{r['state']:<12}{age:<12}{r['dirty']:>6}{mark}")

    missing = [r for r in rows if not r["exists"]]
    stale = [r for r in rows if r["exists"] and r["age"] is not None and r["age"] > args.stale]
    dirty = [r for r in rows if r["dirty"]]

    print("-" * 74)
    print(f"显示 {shown} · 未拉取 {len(missing)} · 停滞(>{args.stale}天) {len(stale)} · 有未提交 {len(dirty)}")
    if dirty:
        print("未提交：" + "、".join(f"{r['id']}({r['dirty']})" for r in dirty))

    ledger = ROOT / ".memory" / "ledger.jsonl"
    if ledger.exists():
        n = sum(1 for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip())
        print(f"记忆账本：{n} 条")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
