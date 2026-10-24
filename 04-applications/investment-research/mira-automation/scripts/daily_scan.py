#!/usr/bin/env python3
"""Mira 每日热点扫描 —— 同花顺强势股归因 → 去重 → 排队研究

定时运行：每个交易日 15:30（收盘后）
    launchd plist: ~/Library/LaunchAgents/com.mira.daily-scan.plist

数据源：同花顺热点 API（HTTP，零鉴权，73ms）
    http://zx.10jqka.com.cn/event/api/getharden/
"""

import json
import time
import sys
from datetime import date, timedelta
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────
MIRA_ROOT = Path(__file__).resolve().parent.parent  # Mira 项目根
CASES_DIR = MIRA_ROOT / "cases" / "auto"
INDEX_FILE = CASES_DIR / "hotspot_index.json"
MAX_PER_DAY = 5              # 每天最多研究几只
MIN_PCT = 3.0                # 最低涨幅
MIN_AMOUNT_YI = 2.0          # 最低成交额（亿）
MAX_RECENT_DAYS = 7          # N 天内已研究过就跳过
EXCLUDE_PREFIXES = ("*ST", "ST", "N", "C")  # 排除 ST/新股/次新

# ── 数据拉取 ──────────────────────────────────────────
def fetch_hotspot(date_str: str | None = None) -> dict:
    """拉取同花顺当日强势股归因。"""
    import urllib.request

    if date_str is None:
        date_str = date.today().strftime("%Y-%m-%d")

    url = (
        f"http://zx.10jqka.com.cn/event/api/getharden/"
        f"date/{date_str}/orderby/date/orderway/desc/charset/GBK/"
    )
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0 Safari/537.36"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("gbk")
    data = json.loads(raw)
    if data.get("errocode", 0) != 0:
        raise RuntimeError(f"同花顺热点 API 错误: {data.get('errormsg', '')}")
    return data


def load_studied_tickers(days: int = MAX_RECENT_DAYS) -> set[str]:
    """加载近 N 天已研究过的 ticker 列表。"""
    studied = set()
    if not INDEX_FILE.exists():
        return studied
    index = json.loads(INDEX_FILE.read_text())
    for date_str, tickers in index.get("studied", {}).items():
        try:
            d = date.fromisoformat(date_str)
            if (date.today() - d).days <= days:
                studied.update(tickers)
        except ValueError:
            continue
    return studied


def save_studied(date_str: str, tickers: list[str]):
    """更新热点索引。"""
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    index = {}
    if INDEX_FILE.exists():
        index = json.loads(INDEX_FILE.read_text())
    index.setdefault("studied", {})[date_str] = tickers
    index["last_updated"] = date.today().isoformat()
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2))


# ── 筛选逻辑 ──────────────────────────────────────────
def filter_candidates(raw_data: dict) -> list[dict]:
    """从原始数据中筛选候选标的。"""
    studied = load_studied_tickers()
    candidates = []
    used_reasons = set()

    for item in raw_data.get("data", []):
        name = item.get("name", "")
        code = item.get("code", "")

        # 排除 ST/新股
        if name.startswith(EXCLUDE_PREFIXES):
            continue
        # 排除已研究
        if code in studied:
            continue

        reason = item.get("reason", "")
        # 同一题材只取一只（按列表顺序优先——涨幅降序）
        primary_tag = reason.split("+")[0] if "+" in reason else reason
        if primary_tag in used_reasons:
            continue

        candidates.append({
            "code": code,
            "name": name,
            "reason": reason,
            "market": item.get("market", 0),
        })
        used_reasons.add(primary_tag)

        if len(candidates) >= MAX_PER_DAY * 2:  # 候选池设上限
            break

    return candidates[:MAX_PER_DAY]


# ── 主流程 ────────────────────────────────────────────
def main():
    today_str = date.today().strftime("%Y-%m-%d")
    print(f"[{today_str}] Mira 每日热点扫描")
    print("-" * 50)

    # 1. 拉热点
    print("1/4 拉取同花顺热点数据...")
    try:
        data = fetch_hotspot(today_str)
        total = len(data.get("data", []))
        print(f"   当日强势股: {total} 只")
    except Exception as e:
        print(f"   ❌ 拉取失败: {e}")
        sys.exit(1)

    # 2. 筛选
    print("2/4 筛选候选标的...")
    candidates = filter_candidates(data)
    if not candidates:
        print("   无符合条件的标的，今日跳过")
        return

    print(f"   候选: {len(candidates)} 只")
    for c in candidates:
        print(f"     {c['code']} {c['name']} → {c['reason']}")

    # 3. 排队研究（串行，每只约 60-90 秒）
    print(f"3/4 开始研究（串行，每只约 60-90s）...")
    studied = []
    try:
        from mira_runner import MiraRunner
        runner = MiraRunner(max_retries=1)
    except ImportError:
        print("   ⚠️  无法导入 MiraRunner，使用模拟模式")
        runner = None

    for i, c in enumerate(candidates):
        print(f"   [{i+1}/{len(candidates)}] 研究 {c['code']} {c['name']}...")

        if runner is None:
            print(f"       ⚠️  MiraRunner 不可用，跳过")
            studied.append(c['code'])
            continue

        try:
            result = runner.run(
                code=c["code"],
                depth="quick_map",
                date_str=today_str,
            )
            if result.get("validation_passed"):
                print(f"       ✅ 通过 → {result['case_dir']}")
            else:
                print(f"       ⚠️  自检未通过 → {result.get('case_dir', 'N/A')}")
            studied.append(c['code'])
        except Exception as e:
            print(f"       ❌ 失败: {e}")

    # 4. 保存索引
    print("4/4 保存索引...")
    save_studied(today_str, studied)
    print(f"   已记录: {studied}")
    print("-" * 50)
    print("完成!")


if __name__ == "__main__":
    main()
