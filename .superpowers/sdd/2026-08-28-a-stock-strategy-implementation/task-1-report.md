# Task 1 Report

## Changes

- Created the `a-stock-strategy` Python project skeleton with `pyproject.toml` and a `src/strategy` package layout.
- Added frozen domain dataclasses for `MarketState`, `Selection`, `Trade`, and `EquityPoint`.
- Implemented `load_config(path) -> BacktestConfig` with TOML parsing for `data`, `strategy`, `backtest`, `market`, `costs`, and metadata sections.
- Implemented `CsvMarketDataProvider.load() -> pd.DataFrame` with CSV loading, boolean normalization, column canonicalization, date parsing, sorting, and validation.
- Implemented `validate_market_frame(frame) -> None` to reject missing columns, duplicate `(date, symbol)` rows, non-monotonic dates, and non-positive prices.
- Added a baseline TOML config and a valid sample market CSV fixture.
- Added `tests/test_data_contract.py` covering the required contract checks and sample loading.

## Tests And Commands

- Initial RED check:
  - `python3 -m pytest tests/test_data_contract.py -v`
  - Result: failed because `pytest` was not installed in the system interpreter.
- Contract RED check with working test environment:
  - `uv run --python 3.11 --with pytest --with pandas pytest tests/test_data_contract.py -v`
  - Result before implementation: `ModuleNotFoundError: No module named 'strategy'`
- Focused verification:
  - `uv run --python 3.11 --with pytest --with pandas pytest tests/test_data_contract.py -v`
  - Result after implementation: `5 passed in 1.60s`
- Full verification:
  - `uv run --python 3.11 --with pytest --with pandas pytest -q`
  - Result: `5 passed in 0.53s`

## Review Fix Round 1

- Added regression tests for intraday timestamps, non-finite prices, resolved config path metadata, and explicit missing-key handling.
- Tightened `validate_market_frame()` so `date` values must remain day-only and price columns must be finite positive numbers.
- Changed `load_config()` to raise explicit `ValueError` messages for missing required keys and to store a resolved `data_path_resolved` in metadata while preserving the original relative `data.path` value.

### Fix Verification

- Focused verification after the fix:
  - `PYTHONPATH=src uv run --python 3.11 --with pytest --with pandas pytest tests/test_data_contract.py -q`
  - Result: `8 passed in 0.93s`
- Full verification after the fix:
  - `PYTHONPATH=src uv run --python 3.11 --with pytest --with pandas pytest -q`
  - Result: `8 passed in 0.51s`

## Review Fix Round 2

- Added a regression test that feeds a complex-valued price and runs under warning-as-error mode.
- Tightened `validate_market_frame()` to reject complex price inputs before numeric coercion, preventing silent acceptance of non-real data.

### Fix Verification

- Focused verification after the fix:
  - `PYTHONPATH=src uv run --python 3.11 --with pytest --with pandas pytest tests/test_data_contract.py -q`
  - Result: `9 passed in 0.74s`
- Full verification after the fix:
  - `PYTHONPATH=src uv run --python 3.11 --with pytest --with pandas pytest -q`
  - Result: `9 passed in 0.83s`

## Review Fix Round 3

- Added a regression test for complex-valued prices embedded in mixed `object` price columns under warning-as-error mode.
- Tightened `validate_market_frame()` to inspect raw price values before coercion and reject complex values in mixed/object columns without triggering coercion warnings.

### Fix Verification

- Focused verification after the fix:
  - `PYTHONPATH=src uv run --python 3.11 --with pytest --with pandas pytest tests/test_data_contract.py -q`
  - Result: `10 passed in 1.25s`
- Full verification after the fix:
  - `PYTHONPATH=src uv run --python 3.11 --with pytest --with pandas pytest -q`
  - Result: `10 passed in 0.57s`

## Concerns

- The project is declared for Python 3.11+, which matches the validated `uv` runtime used here, but the host system interpreter is older.
- `uv` created a local `.venv` during verification; it was not committed.
- This task only covers the data/config skeleton. Strategy, backtest, evaluation, reporting, and CLI layers are still pending in later tasks.
- `uv.lock` and `__pycache__` directories are generated during verification and should remain untracked.
