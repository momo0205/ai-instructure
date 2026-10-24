#!/usr/bin/env python3
"""Mira 自动清理 —— 删除超过 N 天的自动研究 case

定时运行：每周日凌晨 3:00
    launchd plist: ~/Library/LaunchAgents/com.mira.auto-cleaner.plist
"""

import shutil
import json
from datetime import date, timedelta
from pathlib import Path

MIRA_ROOT = Path(__file__).resolve().parent.parent
AUTO_DIR = MIRA_ROOT / "cases" / "auto"
INDEX_FILE = AUTO_DIR / "hotspot_index.json"
MAX_AGE_DAYS = 30

# 用户标记为保留的 case（不会被清理）
def get_saved_cases() -> set[str]:
    """读取热点索引中被标记为 saved 的 case。"""
    if not INDEX_FILE.exists():
        return set()
    try:
        index = json.loads(INDEX_FILE.read_text())
        return set(index.get("saved", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def clean():
    today = date.today()
    if not AUTO_DIR.exists():
        print("auto/ 目录不存在，跳过")
        return

    saved = get_saved_cases()
    cleaned = 0

    for date_dir in sorted(AUTO_DIR.iterdir()):
        if not date_dir.is_dir():
            continue

        # 检查日期
        try:
            d = date.fromisoformat(date_dir.name)
        except ValueError:
            continue

        age = (today - d).days
        if age <= MAX_AGE_DAYS:
            continue

        # 检查是否有保留标记
        skip = False
        for case_dir in date_dir.iterdir():
            if case_dir.is_dir() and case_dir.name in saved:
                skip = True
                break

        if skip:
            print(f"  保留（saved）: {date_dir.name}")
            continue

        # 清理
        shutil.rmtree(date_dir)
        cleaned += 1
        print(f"  已清理: {date_dir.name} （{age} 天前）")

    # 清理索引中的旧条目
    if INDEX_FILE.exists() and cleaned > 0:
        index = json.loads(INDEX_FILE.read_text())
        studied = index.get("studied", {})
        old_keys = [k for k in studied if (today - date.fromisoformat(k)).days > MAX_AGE_DAYS]
        for k in old_keys:
            del studied[k]
        index["last_cleaned"] = today.isoformat()
        INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2))
        print(f"  索引清理: {len(old_keys)} 条旧记录")

    print(f"总计清理: {cleaned} 个日期目录")


if __name__ == "__main__":
    print(f"[{date.today()}] Mira 自动清理")
    print("-" * 40)
    clean()
    print("完成!")
