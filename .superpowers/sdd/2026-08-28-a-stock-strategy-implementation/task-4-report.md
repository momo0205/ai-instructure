# Task 4 report: 绩效评估与基准比较

## Status

完成。新增 `src/strategy/evaluation.py`、`tests/test_evaluation.py`，并从 `strategy` 包导出 `Metrics` 与 `evaluate`。

## Changes

- `evaluate(result, benchmark_equity=None, risk_free_rate=0.0) -> Metrics` 计算累计收益、按实际日历跨度年化收益、胜率、平均盈利/亏损、盈亏因子、最大回撤、年化波动率、夏普、交易次数和空仓日占比。
- 使用对数收益/expm1 及 Welford 单遍方差算法，避免小收益精度损失和平方和溢出；无效数值被忽略，空序列和单点序列返回明确的零值/空仓默认值。
- 基准支持 `EquityPoint` 序列、日期-权益 pair 序列或映射；仅在策略与基准的共同日期范围内计算基准收益，并返回超额收益。
- 无基准时 `benchmark_return` 与 `excess_return` 为 `None`；风险自由利率按年化输入转换为日收益率，并拒绝非有限或低于 -100% 的输入。

## TDD and verification

- RED: `uv run pytest tests/test_evaluation.py -q` — collection failed with the expected `ModuleNotFoundError: No module named 'strategy.evaluation'` before implementation。
- Focused GREEN: `uv run pytest tests/test_evaluation.py -q` — **4 passed**。
- Full suite: `uv run pytest -q` — **29 passed**。
- `git diff --check` — passed。

## Commit

`feat: add backtest metrics and benchmark comparison`

## Concerns

- `cash_ratio` is defined as the fraction of equity snapshots with zero position value (time-based empty-position ratio), not the fraction of capital held as cash.
- Annualized return uses actual elapsed calendar days (`365 / elapsed_days`), while volatility and Sharpe use 252 trading sessions per year.
- `profit_factor` is `0.0` when no losing trade exists so metrics remain finite and JSON-friendly; it is not interpreted as evidence of zero profitability.
- `uv` created local `uv.lock` and `__pycache__` artifacts during verification; they remain untracked.
- The initial `git pull --ff-only` could not authenticate to the configured SSH remote; implementation proceeded from the existing local HEAD.

## Review fix round 1

- Added regressions for benchmark overlap with a non-overlapping strategy prefix, extreme finite PNL totals and profit-factor ratios, extreme finite equity returns, and invalid PNL exclusion from the win-rate denominator.
- Benchmark excess return now compares strategy and benchmark returns from the same first/last shared dates.
- PNL aggregation uses scaled/capped finite summation and safe ratio/mean helpers; volatility uses scaled Welford variance, with annualized volatility and Sharpe guarded against overflow.
- Win rate uses only finite PNL trades in its denominator while `trade_count` continues to report all trade records. Nonpositive equity values produce a bounded `-1.0` drawdown.

### Review verification

- RED: `uv run pytest tests/test_evaluation.py -q` — **4 failed, 4 passed**, reproducing each reported defect.
- Focused GREEN: `uv run pytest tests/test_evaluation.py -q` — **8 passed**.
- Full suite: `uv run pytest -q` — **33 passed**.
- `git diff --check` — passed.

The review fixes are included in the amended Task 4 commit.
