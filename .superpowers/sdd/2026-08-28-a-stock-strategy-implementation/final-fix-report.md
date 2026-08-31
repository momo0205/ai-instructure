# Final review fix wave

## Changes

- Backtest market-state evaluation now fails closed when the configured index
  is missing, malformed, non-finite, non-positive, or produces a non-finite
  return; this matches recommendation semantics.
- `BacktestEngine.run()` validates the incoming frame before sorting and
  simulation, enforcing daily timestamps, duplicate `(date, symbol)` rows,
  and finite non-positive price rejection. Backtests may carry missing prices
  for execution-time handling, while finite non-positive values remain errors.
- Entry orders only require a valid next-day open and tradability flags. The
  same-day close is not consulted before the open, preventing future-data
  leakage.
- Cross-sectional ranking now rejects invalid/zero prior volume and any
  non-finite feature or score. Rejected symbols carry explicit filter reasons
  into recommendation output and no NaN/inf ranking payload is emitted.
- Optional LLM explanation/summary calls are isolated behind an error boundary;
  provider, network, and serialization failures become report warnings and an
  `error` status while deterministic CSV/JSON/chart artifacts still write.
- Added finite validation for engine market trigger parameters and rank windows,
  minimum volume, and weights. Added comments documenting event timing,
  future-data cutoff, costs, ranking filters, and the optional LLM boundary.

## Verification

- `PYTHONPATH=src uv run --python 3.11 --with pytest --with pandas pytest -q`
  → **54 passed**
- `git diff --check` → passed
- Offline CLI:
  `PYTHONPATH=src uv run --python 3.11 python -m strategy backtest --config configs/baseline.toml --output /tmp/a-stock-strategy-final-report`
  → exit code **0**, deterministic report artifacts generated.

## Follow-up hardening wave (2026-08-31)

- Backtests now emit one deduplicated warning for missing or invalid configured
  index history on every affected point-in-time day, and fail closed if any
  prior index close in that history is malformed.
- `BacktestEngine.run()` requires the complete daily market contract (with a
  narrow compatibility default for fixtures that omit all tradability flags),
  while allowing only open/close missing values for execution-time handling.
- Rank windows are integral positive values, ranking weights are known finite
  fields, and all report JSON numeric serialization converts non-finite values
  to `null` rather than emitting NaN/Infinity.
- LLM provider discovery failures are isolated alongside provider call
  failures, preserving deterministic report artifacts and recording an error
  status/warning.
- Recommendation quality scans are restricted to rows at or before `as_of`;
  future malformed rows no longer affect historical output.

Verification:

- `PYTHONPATH=src pytest -q` → **62 passed**.
- `git diff --check` → passed.
- Offline backtest and recommend CLI commands under Python 3.11 → exit code
  **0**; all expected report artifacts and JSON payloads validated.
