# Chinese Experiment Workspace Implementation Plan

> **For agentic workers:** Follow executing-plans and test-driven-development; delegate the isolated frontend implementation and review the integrated result.

**Goal:** Browse, annotate and compare MLflow experiments inside the Chinese workbench.

**Architecture:** A dedicated research application service calls an isolated MLflow adapter for list and annotation operations. Returned runs are restricted to successful local jobs. Frontend research.js owns the tab and comparisons; existing run detail and copy-request actions are reused.

**Scope:** Latest 200 FINISHED experiments, query/filter, name <=120 and notes <=2000, max four comparisons with period/data/cost differences, Chinese loading/empty/error guidance. Metadata persists in a single MLflow annotation tag. No new strategies, AI, duplicate result database, or automatic full-history backfill.

1. Write failing Python tests for disabled/read failure, local-job filtering, payload validation and annotation persistence adapter; use subprocess fake at app boundary, real MLflow for final acceptance.
2. Add storage/mlflow_research.py for search_runs and atomic JSON annotation tag; application/research.py shapes response and isolates errors.
3. Add GET /api/research-experiments and POST /api/jobs/{id}/experiment-label with existing same-origin guard. Whitelist /research.js.
4. Add independent Chinese experiment tab, on-demand load and four-run comparison (delegated); retain selected items and edits across slow requests, no full-list periodic poll.
5. Run targeted Python/Node checks. Verify real MLflow label survives refresh; browser validates Chinese list, save, compare differences and copy parameters.
6. Add in-page help and update Chinese guide; safely reload local idle service. Keep unrelated concurrent Git edits untouched.
