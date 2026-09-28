# Data workbench Implementation Plan

> Use executing-plans and TDD. User approved the data workbench scope in conversation.

**Goal:** Independent daily market assets beyond the old breadth baseline, with inventory/detail/quality/readiness/task UI.
**Architecture:** Separate asset storage/catalog from existing research dataset repository. Preserve legacy dataset and task contracts; explicit research preparation derives a compatible frozen dataset only for fully covered intersection. HTTP handlers call application services, UI in data-management.js.
**Tech Stack:** Python CSV/JSON, SQLite task queue, vanilla JS, pytest/node/Playwright.

- [x] Add tests for standalone publication without real/breadth, requested vs actual coverage, corrupt raw/hash, gaps, future/reversed ranges, listing and detail validation.
- [x] Implement market_data/assets.py independent prepare/publish and data catalog; keep old repository for explicitly injected legacy integrations.
- [x] Download manager default uses independent assets; provider permits nonmatching security/index calendar for standalone mode, preserving strict legacy defaults. Return actual coverage, stage (no invented percentage).
- [x] Add GET data catalog/detail and POST prepare-research routes; prepare copies asset bounded common coverage into existing validated research publication without altering source. Unknown gaps block preparation with clear message.
- [x] Build data-management.js and four local tabs: overview, securities/details, foundation coverage, tasks. Download independent dates, preview up to100 rows, versions, refresh/full-window update, task stage/retry, current-strategy missing-dependency state.
- [x] Verify focused + full tests and browser recent real stock download, persisted detail, old task compatibility, responsive UI.
- [x] Document usage and limits, scoped commit on current development branch.
