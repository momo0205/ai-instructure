# Task 7 Report: End-to-end acceptance and documentation

## Status

Implemented and committed in `3d1d4167d319fd0af724e1e55811483cd6991ac6` (`docs: document a-share strategy backtest workflow`).

## Delivered

- Added `tests/test_end_to_end.py` covering fixed ETF and dynamic cross-sectional runs on the local sample fixture, aligned benchmark return/excess return metrics, deterministic recommendation choice, all four report artifacts, and CLI execution from outside the project directory.
- Extended `data/sample/market.csv` to six trading days with a second candidate symbol so the dynamic strategy has sufficient point-in-time history and executable signals.
- Added README coverage for installation (uv and venv), both CLI commands, configuration fields, CSV data contract, reproducibility caveat (`generated_at`), Mac launchd/cron deployment, optional future FastAPI read-only layer, security, and the no-auto-trading disclaimer.
- Added explicit offline/reproducibility metadata to `configs/baseline.toml` (`offline`, timezone, seed, benchmark symbol and disabled LLM marker).

## Verification

All commands were run with API-key/provider variables removed where applicable:

```text
uv run --offline pytest -q
.................................................                        [100%]
49 passed in 3.53s
```

Backtest from the project directory:

```text
uv run --offline python -m strategy backtest --config configs/baseline.toml --output /tmp/a-stock-task7-inside.54qbTR
{"output": "/private/tmp/a-stock-task7-inside.54qbTR", "files": ["/tmp/a-stock-task7-inside.54qbTR/trades.csv", "/tmp/a-stock-task7-inside.54qbTR/equity.csv", "/tmp/a-stock-task7-inside.54qbTR/summary.json", "/tmp/a-stock-task7-inside.54qbTR/report.png"], "warnings": ["incomplete trade: open position 588000.SH has no executable exit"]}
```

Backtest from `/tmp` using an explicit project path:

```text
uv run --offline --project /Users/chenmao/Desktop/workspace/ai-instructure/.worktrees/a-stock-strategy/04-applications/investment-research/a-stock-strategy python -m strategy backtest --config /Users/chenmao/Desktop/workspace/ai-instructure/.worktrees/a-stock-strategy/04-applications/investment-research/a-stock-strategy/configs/baseline.toml --output /tmp/a-stock-task7-outside.ANRVNb
{"output": "/private/tmp/a-stock-task7-outside.ANRVNb", "files": ["/tmp/a-stock-task7-outside.ANRVNb/trades.csv", "/tmp/a-stock-task7-outside.ANRVNb/equity.csv", "/tmp/a-stock-task7-outside.ANRVNb/summary.json", "/tmp/a-stock-task7-outside.ANRVNb/report.png"], "warnings": ["incomplete trade: open position 588000.SH has no executable exit"]}
```

Recommendation command:

```text
uv run --offline python -m strategy recommend --config configs/baseline.toml --as-of 2026-08-03
```

It returned `triggered: true`, selected `588000.SH`, and the explicit research-only disclaimer. The dynamic recommendation/CLI parity is asserted in the end-to-end test with a one-day feature-window config.

## Concerns

- The six-day sample intentionally produces a final open-position warning because a last-day signal has no subsequent executable exit; this is expected behavior and is preserved in report warnings.
- Existing generated caches (`__pycache__`, egg-info and `uv.lock`) remain untracked and were not included in the commit.
