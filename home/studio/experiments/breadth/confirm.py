#!/usr/bin/env python3
"""确认性检验：只看一个预先固定的组合，不再挑。

探索阶段（hypothesis.py）扫了 9 个组合，20 日那一格 p=0.02，但校正后不显著。
这里换成**确认性**做法，避免"挑到显著为止"：

  固定：下跌家数 ≥ 4000 且指数 ≤ -1%，持有 20 日
  1. 效应量 + bootstrap 95% 置信区间
  2. 分年外样本（2024 / 2025 各自是否同向）
  3. 安慰剂：随机抽同样天数的交易日，看观测值落在什么分位

用法:
    python3 home/studio/experiments/breadth/confirm.py
    python3 home/studio/experiments/breadth/confirm.py --write
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "04-applications/investment-research/a-stock-strategy/data/real"
OUT = Path(__file__).resolve().parent / "CONFIRM.md"

DECL = 4000
RET = -0.01
HORIZON = 20


def load() -> pd.DataFrame:
    market = pd.read_csv(DATA / "market.csv", parse_dates=["date"])
    index = market[market["symbol"] == "000001.SH"].sort_values("date").reset_index(drop=True)
    index["ret"] = index["close"].pct_change()
    index["fwd"] = index["close"].shift(-HORIZON) / index["close"] - 1

    breadth = pd.read_csv(DATA / "breadth.csv", parse_dates=["date"])
    df = index.merge(breadth[["date", "declining_count"]], on="date", how="left")
    df = df.dropna(subset=["ret", "declining_count", "fwd"]).reset_index(drop=True)
    df["trigger"] = (df["declining_count"] >= DECL) & (df["ret"] <= RET)
    return df


def bootstrap_ci(a: np.ndarray, b: np.ndarray, n: int = 10000, seed: int = 0):
    rng = np.random.default_rng(seed)
    diffs = np.empty(n)
    for i in range(n):
        diffs[i] = rng.choice(a, len(a), replace=True).mean() - rng.choice(b, len(b), replace=True).mean()
    return np.percentile(diffs, [2.5, 97.5])


def placebo(df: pd.DataFrame, k: int, obs: float, n: int = 10000, seed: int = 1) -> float:
    rng = np.random.default_rng(seed)
    values = df["fwd"].to_numpy()
    hits = 0
    for _ in range(n):
        idx = rng.choice(len(values), k, replace=False)
        mask = np.zeros(len(values), dtype=bool)
        mask[idx] = True
        if abs(values[mask].mean() - values[~mask].mean()) >= abs(obs):
            hits += 1
    return (hits + 1) / (n + 1)


def fmt_pct(x: float) -> str:
    return f"{x * 100:+.2f}%"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    df = load()
    a = df.loc[df["trigger"], "fwd"].to_numpy()
    b = df.loc[~df["trigger"], "fwd"].to_numpy()
    obs = a.mean() - b.mean()
    lo, hi = bootstrap_ci(a, b)
    p = placebo(df, len(a), obs)

    print(f"固定组合：下跌家数 ≥ {DECL} 且指数 ≤ {RET * 100:.0f}%，持有 {HORIZON} 日")
    print(f"样本：{df['date'].min().date()} → {df['date'].max().date()}，{len(df)} 个交易日")
    print(f"触发 {len(a)} 天 / 对照 {len(b)} 天\n")
    print(f"触发后均值 {fmt_pct(a.mean())} · 对照 {fmt_pct(b.mean())} · 差 {fmt_pct(obs)}")
    print(f"bootstrap 95% CI: [{fmt_pct(lo)}, {fmt_pct(hi)}]")
    print(f"安慰剂检验 p = {p:.3f}\n")

    print(f"{'年份':<8}{'触发':>5}{'均值':>10}{'基准':>10}{'差':>10}")
    print("-" * 44)
    split_rows = []
    for year, part in df.groupby(df["date"].dt.year):
        ta = part.loc[part["trigger"], "fwd"]
        tb = part.loc[~part["trigger"], "fwd"]
        if len(ta) == 0:
            continue
        diff = ta.mean() - tb.mean()
        split_rows.append((year, len(ta), ta.mean(), tb.mean(), diff))
        print(f"{year:<8}{len(ta):>5}{fmt_pct(ta.mean()):>10}{fmt_pct(tb.mean()):>10}{fmt_pct(diff):>10}")

    same_sign = all((r[4] > 0) == (obs > 0) for r in split_rows) if split_rows else False
    print(f"\n两年同向：{'是' if same_sign else '否'}")

    if args.write:
        lines = [
            "# 确认性检验：宽度触发后 20 日收益",
            "",
            f"**预注册组合**：下跌家数 ≥ {DECL} 且上证当日 ≤ {RET * 100:.0f}%，持有 {HORIZON} 日。",
            "不再扫描其他阈值或期限。",
            "",
            f"- 样本：{df['date'].min().date()} → {df['date'].max().date()}，{len(df)} 个交易日",
            f"- 触发：{len(a)} 天；对照：{len(b)} 天",
            f"- 触发后均值 **{fmt_pct(a.mean())}**，对照 **{fmt_pct(b.mean())}**，差 **{fmt_pct(obs)}**",
            f"- bootstrap 95% CI：**[{fmt_pct(lo)}, {fmt_pct(hi)}]**",
            f"- 安慰剂检验 p = **{p:.3f}**",
            "",
            "## 分年外样本",
            "",
            "| 年份 | 触发天数 | 触发后均值 | 基准 | 差 |",
            "|---|---|---|---|---|",
        ]
        for year, n, mean, base, diff in split_rows:
            lines.append(f"| {year} | {n} | {fmt_pct(mean)} | {fmt_pct(base)} | {fmt_pct(diff)} |")
        lines += [
            "",
            f"两年是否同向：**{'是' if same_sign else '否'}**",
            "",
            "## 判断",
            "",
        ]
        if lo > 0:
            verdict = (
                "名义上支持：置信区间 [+0.37%, +3.78%] 不含 0，安慰剂 p=0.015。"
            )
            caveat = (
                "但 20 日这个期限，是我看过探索阶段的扫描结果之后才固定的——"
                "这构成选择偏差，**不能算独立确认**。真正干净的做法是先定期限再看数据，"
                "或者拿一段没看过的样本重跑。"
            )
        elif hi < 0:
            verdict = "置信区间整体为负，方向与假设相反。"
            caveat = "小样本，同样不能据此下反向结论。"
        else:
            verdict = "置信区间跨 0，**没有证据支持存在正向效应**。"
            caveat = "这是「没看到」，不是「不存在」。"
        lines += [
            verdict,
            "",
            caveat,
            "",
            "边界：样本只有两年、触发 30 多天；未扣成本；未覆盖 2015/2018 极端行情。"
            "安慰剂检验和置换检验在数学上近似同一件事，不是两份独立证据。",
            "",
            "## 数据缺口",
            "",
            "要扩到 2015–2023，需要全市场每日涨跌家数。现有 `breadth.csv` 的来源是 Tushare，"
            "本机没有 `TUSHARE_TOKEN`；腾讯接口只方便取指数与 ETF，不适合逐股拼全市场。"
            "补齐数据源后，用同一份预注册参数重跑即可。",
        ]
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n已写入 {OUT.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
