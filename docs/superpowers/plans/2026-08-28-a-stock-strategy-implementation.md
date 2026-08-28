# A 股策略回测系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个无需大模型 API Key 即可运行的 A 股日线事件驱动回测系统，比较固定科创 50 ETF 与动态选股策略，并输出推荐与静态报告。

**Architecture:** 在 `04-applications/investment-research/a-stock-strategy` 建立独立 Python 包。数据、领域模型、策略、回测、评估、报告和可选 LLM 层通过小接口解耦；CLI 负责组装配置并输出 artifacts。

**Tech Stack:** Python 3.11+, pandas, numpy, matplotlib, pydantic, pytest, tomllib（配置读取）。第一版不要求联网或外部 API Key。

**Spec:** `docs/superpowers/specs/2026-08-28-a-stock-strategy-design.md`

## Global Constraints

- 回测只使用日线数据；信号在收盘后生成，下一交易日执行。
- 核心回测、规则选股和静态报告不依赖大模型 API Key 或网络。
- 禁止未来数据泄漏；所有数据口径和成本参数写入报告元数据。
- 不接券商 API、不自动下单、不把结果表述为投资建议。
- 所有实现按 TDD：先写失败测试，确认失败后写最小实现。

### Task 1: 项目骨架、配置与数据契约

**Files:**
- Create: `04-applications/investment-research/a-stock-strategy/pyproject.toml`
- Create: `04-applications/investment-research/a-stock-strategy/src/strategy/__init__.py`
- Create: `04-applications/investment-research/a-stock-strategy/src/strategy/config.py`
- Create: `04-applications/investment-research/a-stock-strategy/src/strategy/domain.py`
- Create: `04-applications/investment-research/a-stock-strategy/src/strategy/data.py`
- Create: `04-applications/investment-research/a-stock-strategy/configs/baseline.toml`
- Create: `04-applications/investment-research/a-stock-strategy/data/sample/market.csv`
- Test: `04-applications/investment-research/a-stock-strategy/tests/test_data_contract.py`

**Interfaces:** `load_config(path) -> BacktestConfig`; `CsvMarketDataProvider.load() -> pd.DataFrame`; `validate_market_frame(frame) -> None`; domain dataclasses `MarketState`, `Selection`, `Trade`, `EquityPoint`。

- [ ] **Step 1: Write failing tests** for required columns, duplicate `(date,symbol)`, non-positive prices, config parsing, and valid sample loading.
- [ ] **Step 2: Run** `pytest tests/test_data_contract.py -v` and confirm failure because package is absent.
- [ ] **Step 3: Implement** dataclasses, TOML parsing, CSV loading and explicit validation errors.
- [ ] **Step 4: Run** the focused test and then `pytest -q`; expect PASS.
- [ ] **Step 5: Commit** `feat: add strategy project skeleton and market data contract`.

### Task 2: 市场事件判定与策略接口

**Files:**
- Create: `src/strategy/signals.py`
- Create: `src/strategy/strategies/base.py`
- Create: `src/strategy/strategies/fixed.py`
- Create: `src/strategy/strategies/rank.py`
- Test: `tests/test_strategies.py`

**Interfaces:** `MarketTrigger.evaluate(index_level, index_return_1d) -> MarketState`; `Strategy.select(as_of, market, universe) -> Selection | None`; `FixedAssetStrategy`; `CrossSectionalRankStrategy`。

- [ ] **Step 1: Write failing tests** for 4000+ and negative return trigger, fixed ETF selection, feature-only-up-to-`as_of` ranking, filtering suspended/limit-up symbols, and empty selection.
- [ ] **Step 2: Run** `pytest tests/test_strategies.py -v` and confirm expected missing-module failures.
- [ ] **Step 3: Implement** deterministic trigger and scoring using configurable momentum, reversal, volatility and volume weights; include feature values and reason.
- [ ] **Step 4: Run** focused and full tests; expect PASS.
- [ ] **Step 5: Commit** `feat: add market trigger and pluggable selection strategies`.

### Task 3: 日线回测撮合引擎

**Files:**
- Create: `src/strategy/backtest.py`
- Test: `tests/test_backtest.py`

**Interfaces:** `BacktestEngine.run(market_data, strategy) -> BacktestResult`; `BacktestResult.trades`, `.equity`, `.warnings`。

- [ ] **Step 1: Write failing tests** for next-day-open entry, one-day hold exit, cash/position accounting, commission/tax/slippage, no future data, and suspended/limit-up non-execution.
- [ ] **Step 2: Run** `pytest tests/test_backtest.py -v` and confirm RED.
- [ ] **Step 3: Implement** chronological event loop with pending orders, explicit execution prices, configurable costs, and incomplete-trade warnings.
- [ ] **Step 4: Run** focused and full tests; expect PASS with no warnings except intentionally tested cases.
- [ ] **Step 5: Commit** `feat: add event-driven daily backtest engine`.

### Task 4: 绩效评估与基准比较

**Files:**
- Create: `src/strategy/evaluation.py`
- Test: `tests/test_evaluation.py`

**Interfaces:** `evaluate(result, benchmark_equity=None, risk_free_rate=0.0) -> Metrics`。

- [ ] **Step 1: Write failing tests** for cumulative/annualized return, win rate, profit factor, max drawdown, volatility, Sharpe, trade count, cash ratio and excess return.
- [ ] **Step 2: Run** focused tests and confirm RED.
- [ ] **Step 3: Implement** numerically stable metrics with explicit empty/one-point behavior and aligned benchmark dates.
- [ ] **Step 4: Run** focused and full tests; expect PASS.
- [ ] **Step 5: Commit** `feat: add backtest metrics and benchmark comparison`.

### Task 5: 报告、推荐和 CLI

**Files:**
- Create: `src/strategy/reporting.py`
- Create: `src/strategy/recommendation.py`
- Create: `src/strategy/cli.py`
- Create: `src/strategy/__main__.py`
- Create: `tests/test_reporting_cli.py`

**Interfaces:** `write_report(result, metrics, output_dir) -> ReportPaths`; `recommend(as_of, data, strategy) -> Recommendation`; CLI commands `backtest` and `recommend`。

- [ ] **Step 1: Write failing tests** asserting `trades.csv`, `equity.csv`, `summary.json`, `report.png` contents and CLI exit/output for both commands.
- [ ] **Step 2: Run** focused tests and confirm RED.
- [ ] **Step 3: Implement** deterministic CSV/JSON serialization, matplotlib charts, recommendation ranking with filter reasons, and argparse CLI.
- [ ] **Step 4: Run** focused tests plus an end-to-end sample command; expect all artifacts and PASS.
- [ ] **Step 5: Commit** `feat: add reports recommendations and command line interface`.

### Task 6: 可选 LLM 解释适配器

**Files:**
- Create: `src/strategy/llm.py`
- Create: `tests/test_llm.py`
- Modify: `src/strategy/reporting.py`

**Interfaces:** `LLMProvider.explain_recommendation(result) -> str`; `.summarize_backtest(report) -> str`; `NoopLLMProvider`; `OpenAICompatibleLLMProvider` loaded only when explicitly configured.

- [ ] **Step 1: Write failing tests** proving Noop provider works without environment variables, metadata records disabled status, and provider output cannot mutate metrics or trades.
- [ ] **Step 2: Run** focused tests and confirm RED.
- [ ] **Step 3: Implement** protocol, no-op default and optional adapter boundary; do not import or call a model when disabled.
- [ ] **Step 4: Run** focused and full tests; expect PASS without API Key.
- [ ] **Step 5: Commit** `feat: add optional llm explanation provider`.

### Task 7: 端到端验收与文档

**Files:**
- Create: `04-applications/investment-research/a-stock-strategy/README.md`
- Create: `tests/test_end_to_end.py`
- Modify: `configs/baseline.toml`

- [ ] **Step 1: Write failing end-to-end test** running fixed and dynamic strategies on the fixture and asserting benchmark comparison plus all four artifacts.
- [ ] **Step 2: Run** the test and confirm RED until CLI/report wiring is complete.
- [ ] **Step 3: Implement** usage docs, configuration reference, data format example, reproducibility notes and disclaimer.
- [ ] **Step 4: Run** `pytest -q` and both CLI commands from a clean environment; record exact output.
- [ ] **Step 5: Commit** `docs: document a-share strategy backtest workflow`.

## Verification Checklist

- [ ] `pytest -q` passes.
- [ ] Sample backtest runs without network or API Key.
- [ ] Fixed ETF and dynamic strategy both produce comparable metrics.
- [ ] Recommendation output matches the strategy choice for the same `as_of` date.
- [ ] Reports contain data range, adjustment basis, costs and generation timestamp.
- [ ] No claims of profitability or investment advice are made in CLI/docs.
