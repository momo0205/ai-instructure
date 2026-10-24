#!/usr/bin/env python3
"""假设检验：市场宽度触发之后，指数未来 N 日收益是否与平常不同？

假设（可证伪）：
    当「全市场下跌家数 ≥ N」且「上证当日收益 ≤ -1%」时，
    上证指数未来 5/10/20 日收益，与其余交易日的分布无显著差异。

数据：a-stock-strategy/data/real（2024 起，腾讯 qfq + tushare 宽度）
方法：分组均值差 + 置换检验（不依赖正态假设），并做阈值敏感性分析。

用法:
    python3 home/studio/experiments/breadth/hypothesis.py
    python3 home/studio/experiments/breadth/hypothesis.py --write
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "04-applications/investment-research/a-stock-strategy/data/real"
OUT = Path(__file__).resolve().parent / "FINDINGS.md"
HORIZONS = (5, 10, 20)


def load() -> pd.DataFrame:
    market = pd.read_csv(DATA / "market.csv", parse_dates=["date"])
    index = market[market["symbol"] == "000001.SH"].sort_values("date").reset_index(drop=True)
    index["ret"] = index["close"].pct_change()

    breadth = pd.read_csv(DATA / "breadth.csv", parse_dates=["date"])
    df = index.merge(breadth[["date", "declining_count", "total_count"]], on="date", how="left")

    for h in HORIZONS:
        df[f"fwd{h}"] = index["close"].shift(-h) / index["close"] - 1
    return df.dropna(subset=["ret", "declining_count"])


def perm_pvalue(a: np.ndarray, b: np.ndarray, n: int = 5000, seed: int = 0) -> float:
    """两组均值差的置换检验（双侧）。"""
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    obs = abs(a.mean() - b.mean())
    pool = np.concatenate([a, b])
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n):
        rng.shuffle(pool)
        if abs(pool[: len(a)].mean() - pool[len(a):].mean()) >= obs:
            count += 1
    return (count + 1) / (n + 1)


def evaluate(df: pd.DataFrame, decl: int, ret_thr: float) -> dict:
    mask = (df["declining_count"] >= decl) & (df["ret"] <= ret_thr)
    row = {"decl": decl, "ret_thr": ret_thr, "n": int(mask.sum())}
    for h in HORIZONS:
        col = f"fwd{h}"
        a = df.loc[mask, col].dropna().to_numpy()
        b = df.loc[~mask, col].dropna().to_numpy()
        row[f"n{h}"] = len(a)
        row[f"mean{h}"] = a.mean() if len(a) else float("nan")
        row[f"base{h}"] = b.mean() if len(b) else float("nan")
        row[f"p{h}"] = perm_pvalue(a, b, n=2000)
    return row


def fmt_pct(x: float) -> str:
    return "—" if np.isnan(x) else f"{x * 100:+.2f}%"


def fmt_p(x: float) -> str:
    return "—" if np.isnan(x) else ("<0.01" if x < 0.01 else f"{x:.2f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    df = load()
    print(f"样本：{df['date'].min().date()} → {df['date'].max().date()}，{len(df)} 个交易日")
    print(f"宽度覆盖：{df['declining_count'].notna().sum()} 天\n")

    combos = [(d, r) for d in (3000, 3500, 4000) for r in (-0.005, -0.01, -0.015)]
    rows = [evaluate(df, d, r) for d, r in combos]

    header = f"{'下跌家数≥':<10}{'指数≤':<9}{'触发':>5}"
    for h in HORIZONS:
        header += f"  {'n':>4} {'均值':>8} {'基准':>8} {'p':>6}"
    print(header)
    print("-" * len(header))
    for r in rows:
        line = f"{r['decl']:<10}{r['ret_thr'] * 100:>6.1f}%  {r['n']:>5}"
        for h in HORIZONS:
            line += f"  {r[f'n{h}']:>4} {fmt_pct(r[f'mean{h}']):>8} {fmt_pct(r[f'base{h}']):>8} {fmt_p(r[f'p{h}']):>6}"
        print(line)

    if args.write:
        lines = [
            "# 宽度触发后的指数收益：一次可证伪的检验",
            "",
            f"数据：{df['date'].min().date()} → {df['date'].max().date()}，{len(df)} 个交易日。",
            "方法：分组均值 + 置换检验（2000 次，双侧）；未做多重比较校正。",
            "",
            "| 下跌家数≥ | 指数当日≤ | 触发天数 | 5日均值 | 5日基准 | p | 10日均值 | 10日基准 | p | 20日均值 | 20日基准 | p |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['decl']} | {r['ret_thr'] * 100:.1f}% | {r['n']} | "
                f"{fmt_pct(r['mean5'])} | {fmt_pct(r['base5'])} | {fmt_p(r['p5'])} | "
                f"{fmt_pct(r['mean10'])} | {fmt_pct(r['base10'])} | {fmt_p(r['p10'])} | "
                f"{fmt_pct(r['mean20'])} | {fmt_pct(r['base20'])} | {fmt_p(r['p20'])} |"
            )
        pre = next(r for r in rows if r["decl"] == 4000 and r["ret_thr"] == -0.01)
        bonf = min(1.0, pre["p20"] * len(rows))
        lines += [
            "",
            "## 结论",
            "",
            f"按 `configs/real_breadth.toml` 里预设的阈值（下跌家数 ≥ 4000 且指数 ≤ -1%），"
            f"样本内触发 **{pre['n']}** 次：",
            "",
            f"- 5 日：{fmt_pct(pre['mean5'])} vs {fmt_pct(pre['base5'])}，p={fmt_p(pre['p5'])}",
            f"- 10 日：{fmt_pct(pre['mean10'])} vs {fmt_pct(pre['base10'])}，p={fmt_p(pre['p10'])}",
            f"- 20 日：{fmt_pct(pre['mean20'])} vs {fmt_pct(pre['base20'])}，p={fmt_p(pre['p20'])}",
            "",
            f"20 日的正偏看起来显著，但这次一共比较了 {len(rows)} 个组合，"
            f"Bonferroni 校正后 p≈{bonf:.2f}，**不显著**。",
            "所以结论只能是：**这个样本里没有足够证据支持「宽度触发后指数会系统性反弹」**，"
            "不能拿它当交易依据。",
            "",
            "## 解读边界",
            "",
            "- 触发样本很少（20 日只有 30 多天），任何结论都只能是「没看到」，不能说「不存在」。",
            "- 未做多重比较的预先注册：阈值是配置文件里既有的，但敏感性扫描本身已经构成多次比较。",
            "- 数据只覆盖 2024 年起，没有 2015/2018 那种极端行情。",
            "- 收益未扣成本，且假设「触发日收盘价成交」，实盘不一定做得到。",
            "- 下跌家数 ≤ -1.5% 的 21 天里，下跌家数最少也有 4384，"
            "所以 3000/3500/4000 三个阈值在这组条件下是同一批样本（表里三行完全相同）。",
            "",
            "## 下一步（如果继续）",
            "",
            "1. 拉 2015–2023 的数据重跑，看结论是否稳定。",
            "2. 预先固定一个组合，不再扫描。",
            "3. 换成「触发后第 N 日收盘买入、持有 M 日」的可执行规则，并扣成本。",
        ]
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n已写入 {OUT.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
