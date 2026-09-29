# Technical Analysis Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a categorized indicator library and an independent technical analysis workspace for one immutable market asset at a time.

**Architecture:** A trusted Python catalog owns metadata and calculations. An application service verifies a published asset, aligns its security and observed index dates, then returns immutable source metadata and daily indicator values. The existing local web server exposes this service; a separate browser module renders the catalog, chart, date inspector and data table.

**Tech Stack:** Python 3.11, pandas, stdlib HTTP server, plain JavaScript, SVG, pytest, Node test runner.

**Spec:** `docs/superpowers/specs/2026-09-28-technical-analysis-foundation-design.md`

## Shared constraints

- Read only one `asset_*` version per request; never combine adjustment bases or require market breadth.
- A maximum of 12 derived indicator instances and 5,000 full-history calendar positions; no silent EMA truncation.
- Indicators use continuous valid observations, `sma` and `volume_sma` windows 2–252, `ema` SMA seed, `bollinger` population standard deviation and multiplier 0–10 exclusive of zero.
- Output only finite JSON values or `null`; unavailable values carry a reason. Calculations never generate buy or sell advice.
- The indicator library has stable categories and metadata for the page and service. Raw OHLC, volume and amount are source data.

## Task 1: Trusted indicator library

**Files:** Create `src/strategy/indicators/catalog.py`, `src/strategy/indicators/series.py`; modify `src/strategy/indicators/__init__.py`; create `tests/test_technical_indicators.py`.

- [ ] Write tests first for catalog category, defensive copies, strict parameter and instance validation, hand calculated SMA/EMA/Bollinger/volume SMA, short and broken windows, independent field validity, and old `simple_moving_average` compatibility.
- [ ] Run `.venv/bin/pytest -q tests/test_technical_indicators.py` and confirm the new assertions fail for missing behavior.
- [ ] Implement `indicator_catalog() -> list[dict]`, `normalize_instances(value: object) -> list[dict]`, and `calculate_series(rows: list[dict], instances: list[dict]) -> dict[str, list[dict]]`. Each output position has `value`/`values`, `reason`, and `available`; metadata declares category, formula, input, output and warmup.
- [ ] Run `.venv/bin/pytest -q tests/test_technical_indicators.py tests/test_exit_policies.py` and check all tests pass.

## Task 2: Verified asset analysis service

**Files:** Create `src/strategy/application/technical_analysis.py`; modify `src/strategy/market_data/assets.py` only to share secure asset reading if necessary; create `tests/test_technical_analysis.py`.

- [ ] Write tests first for independent stock only assets, observed index gaps, source and adjustment isolation, display start independent of EMA seed, invalid ranges/IDs/symbols, tampered hash and duplicate dates, and 5,000 day limit.
- [ ] Run `.venv/bin/pytest -q tests/test_technical_analysis.py` and confirm feature failures.
- [ ] Implement `TechnicalAnalysisService(root).analyze(request: dict) -> dict` to verify path and hash, load one version, align calendar, calculate over full history, filter only output dates, and return normalized request/source/calendar/rows/instance metadata.
- [ ] Run `.venv/bin/pytest -q tests/test_technical_analysis.py tests/test_assets.py` and check all tests pass.

## Task 3: HTTP catalog and analysis endpoints

**Files:** Modify `src/strategy/interfaces/web/server.py`; create `tests/test_technical_analysis_api.py`.

- [ ] Write dispatch tests for `GET /api/indicators`, `POST /api/technical-analysis`, validation diagnostics, unavailable assets and strict JSON encoding.
- [ ] Run `.venv/bin/pytest -q tests/test_technical_analysis_api.py` and confirm endpoint failures.
- [ ] Register the catalog, source-list, and analysis endpoints using the existing `dispatch` error handling; preserve origin and JSON write guards.
- [ ] Run `.venv/bin/pytest -q tests/test_technical_analysis_api.py tests/test_web.py` and check all tests pass.

## Task 4: Indicator library and visual analysis workspace

**Files:** Create `src/strategy/interfaces/web/static/technical-analysis.js`; modify `src/strategy/interfaces/web/static/index.html`, `style.css`, `data-management.js`, `server.py`; create `tests/technical-analysis.test.cjs`.

- [ ] Write Node tests first for category browsing and instance creation, request construction, stale result rejection, table pagination, JSON export, and asset detail navigation.
- [ ] Run `node --test tests/technical-analysis.test.cjs` and confirm missing behavior fails.
- [ ] Build a technical analysis tab with categorized library, asset/version picker, date range, editable instance parameters, SVG OHLC/indicator/volume charts with shared cursor and range controls, source metadata, daily inspector, paginated exact values and JSON export. Asset detail opens the same tab with its version selected.
- [ ] Run `node --test tests/technical-analysis.test.cjs tests/data-management.test.cjs tests/tabs.test.cjs` and check all tests pass.

## Task 5: Acceptance and documentation

**Files:** Modify `README.md` and any test fixture required by acceptance.

- [ ] Run full `.venv/bin/pytest -q`, `node --test tests/*.test.cjs`, `node --check src/strategy/interfaces/web/static/technical-analysis.js`, and `git diff --check`; resolve only concrete failures.
- [ ] Exercise the local browser flow: choose security/version, change range and indicator parameters, inspect a date, export JSON and check narrow layout. Record any unmet acceptance item explicitly.
- [ ] Update README with the independent technical analysis workflow, indicator library definitions and data caveats.
- [ ] Commit only the A stock strategy files created or changed for this feature and push the feature branch after verification.

## Review focus

Check malicious version IDs, tampered manifests, duplicate indicator IDs, invalid numeric inputs, and stale browser responses against their owning task's tests. Confirm the output never implies an unavailable value is zero and that a source version remains visible throughout the workflow.

## Verification record (2026-09-29)

The feature and review fixes passed 511 Python tests, 96 Node tests, JavaScript syntax check, and `git diff --check`. The live API returned four independent source versions and a 16-day analysis for an existing Tencent asset. The browser previously rendered the catalog, analysis, charts, and table with a real asset; final narrow-screen and export interaction could not be repeated because the computer-use bridge stopped starting. Their request/export logic and responsive CSS were inspected and covered by unit tests, but visual mobile acceptance remains open.
