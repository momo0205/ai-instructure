#!/usr/bin/env python3
"""宽度过滤 A/B 的结果整理。

前置：先跑两次回测（在 a-stock-strategy 目录下）

    .venv/bin/python -m strategy compare \
        --config configs/ab_breadth_on.toml \
        --output <worktree>/home/studio/experiments/breadth/ab/on
    .venv/bin/python -m strategy compare \
        --config configs/ab_breadth_off.toml \
        --output <worktree>/home/studio/experiments/breadth/ab/off

然后：

    python3 home/studio/experiments/breadth/ab.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DATA = ROOT / "04-applications/investment-research/a-stock-strategy/data/real"
OUT = HERE / "AB.md"


def load_metrics(run: str) -> dict:
    path = HERE / "ab" / run / "comparison.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {name: s["metrics"] for name, s in data["strategies"].items()}


def next_day_effect() -> list[tuple[str, float, float, int]]:
    """触发日「次日」收益 vs 其余交易日，按标的拆开。"""
    market = pd.read_csv(DATA / "market.csv", parse_dates=["date"])
    breadth = pd.read_csv(DATA / "breadth.csv", parse_dates=["date"])

    index = market[market["symbol"] == "000001.SH"][["date", "close"]].sort_values("date")
    index = index.reset_index(drop=True)
    index["ret"] = index["close"].pct_change()
    frame = index.merge(breadth[["date", "declining_count"]], on="date")
    frame["trigger"] = (frame["declining_count"] >= 4000) & (frame["ret"] <= -0.01)

    rows = []
    for symbol in ("588000.SH", "510300.SH", "159915.SZ"):
        bars = market[market["symbol"] == symbol][["date", "close"]].sort_values("date").reset_index(drop=True)
        bars["next"] = bars["close"].shift(-1) / bars["close"] - 1
        merged = frame[["date", "trigger"]].merge(bars[["date", "next"]], on="date")
        a = merged.loc[merged["trigger"], "next"].dropna()
        b = merged.loc[~merged["trigger"], "next"].dropna()
        rows.append((symbol, a.mean(), b.mean(), len(a)))
    return rows


def pct(x: float) -> str:
    return f"{x * 100:+.2f}%"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    on, off = load_metrics("on"), load_metrics("off")
    names = ["fixed_asset", "cross_sectional_rank"]

    print(f"{'策略':<24}{'配置':<8}{'累计':>9}{'年化':>9}{'最大回撤':>10}{'Sharpe':>8}{'交易':>6}{'空仓':>7}")
    print("-" * 82)
    for name in names:
        for label, run in (("过滤开", on), ("过滤关", off)):
            m = run[name]
            print(f"{name:<24}{label:<8}{pct(m['cumulative_return']):>9}{pct(m['annualized_return']):>9}"
                  f"{pct(m['max_drawdown']):>10}{m['sharpe_ratio']:>8.2f}{m['trade_count']:>6}{m['cash_ratio']*100:>6.1f}%")

    print("\n触发日「次日」收益（按标的）")
    effects = next_day_effect()
    for symbol, trig, other, n in effects:
        print(f"  {symbol}: 触发 {pct(trig)}  其余 {pct(other)}  差 {pct(trig - other)}  n={n}")

    if args.write:
        lines = [
            "# 宽度过滤 A/B：它到底贡献了什么",
            "",
            "同一份 `real_breadth` 配置，**只改 `[market]`**：",
            "",
            "| 配置 | 触发条件 |",
            "|---|---|",
            "| `ab_breadth_on.toml` | 下跌家数 ≥ 4000 且上证 ≤ -1% |",
            "| `ab_breadth_off.toml` | 下跌家数 ≥ 0 且上证 ≤ +100%（即每天都触发） |",
            "",
            "数据 2024-01-03 → 2025-12-31；成本按配置（佣金 0.03%、最低 5 元、滑点 2bp）；",
            "信号在收盘产生、次日开盘成交。",
            "",
            "## 结果",
            "",
            "| 策略 | 配置 | 累计 | 年化 | 最大回撤 | Sharpe | 交易数 | 空仓比例 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for name in names:
            for label, run in (("过滤开", on), ("过滤关", off)):
                m = run[name]
                lines.append(
                    f"| `{name}` | {label} | {pct(m['cumulative_return'])} | {pct(m['annualized_return'])} | "
                    f"{pct(m['max_drawdown'])} | {m['sharpe_ratio']:.2f} | {m['trade_count']} | {m['cash_ratio']*100:.1f}% |"
                )
        lines += [
            "",
            "## 三个解读",
            "",
            "1. **过滤器的本质是减仓开关**：空仓比例从 50% 提到 93%–94%，最大回撤随之下降"
            "（fixed_asset −44.0% → −27.2%），但收益也一起下降。它控制的是暴露，不是选时。",
            "",
            "2. **对动态选股是负贡献**：`cross_sectional_rank` 从 **+29.9%** 变成 **−14.4%**，"
            "Sharpe 从 +0.77 变成 −0.96。原因是它 94% 的时间在空仓，而触发的那 30 天并没有更好——"
            "过滤器把大部分赚钱的日子挡在门外。",
            "",
            "3. **对固定标的（科创50）它挑的日子更差**：触发日的「次日」收益，"
            "588000.SH 是 −0.18%，其余日子 +0.15%（差 −0.33%）；"
            "而 510300.SH / 159915.SZ 几乎没差别。也就是说，这个过滤器对科创50 是负向的。",
            "",
            "## 结论",
            "",
            "- 在这个样本里，**「宽度触发」没有提供选时 alpha**；它是降低暴露的开关。",
            "- 目标是控回撤 → 它有效；目标是收益 → 它有害（对动态策略尤其明显）。",
            "- 之前统计上的 20 日正偏（+2.08%）没有转化成 1 日持有策略的收益："
            "**期限不匹配、标的不匹配**，两个都会让结论失效。",
            "",
            "## 边界",
            "",
            "- 只有两年、一种市场状态；未做参数搜索（这次是刻意不搜）。",
            "- 1 日持有 + 次日开盘成交；换成更长持有期结论可能不同。",
            "- `benchmark_return` 为 null，无法计算真正的超额收益。",
            "- 不能据此直接改默认配置；需要更长样本和更多标的。",
        ]
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n已写入 {OUT.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
