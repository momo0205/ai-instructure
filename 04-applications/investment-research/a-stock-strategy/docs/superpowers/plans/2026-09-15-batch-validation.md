# Batch Holding-Period Validation Implementation Plan

> **For agentic workers:** Use executing-plans and test-driven-development; frontend implementation is an independent delegated task.

**Goal:** Compare 2–8 holding periods on an earlier period, select one without consulting the later period, then validate it on that later period.

**Architecture:** StudyManager persists group state and orchestrates existing JobManager jobs. It copies the base successful task's frozen market once and captures current code once, so every member uses identical input files. MLflow receives study ID and phase on normal result exports. Server composes managers; no extra calculation engine.

**Contract:** POST /api/studies {base_job_id,holding_periods,validation_start}; GET list/detail; POST cancel. Date boundary is mapped to first actual session on/after validation_start; selection ends at preceding session. Both periods have at least two sessions. Parameters are unique integers 1–252, count2–8. A completed trade is required for selection, criterion highest cumulative return, tie shorter hold. All training jobs must succeed before selection; no eligible candidate means no validation. Validation runs one locked choice with fresh initial cash, no inherited position and effectiveness=false. No promise of profitability or untouched data across repeated studies.

1. Add tests/test_studies.py: no validation before selection, tie/zero-trade/failure, fixed input snapshot, restart and cancellation, real engine small sample.
2. Add application/studies.py: persistent group state, bounded selection, coordinator thread and cancellation. Interrupted groups stay inspectable after restart and are not silently resumed.
3. Add JobManager.submit_frozen private service capability; save study context before queue publication. Add result metadata and MLflow params/tags for group linkage.
4. Compose StudyManager in web server and add endpoints plus static studies.js whitelist. Frontend adds batch form, progress/history and separated train/validation metrics (delegated).
5. Run relevant Python and Node checks; independent code review for phase isolation/concurrency. Browser creates a sample batch, verifies winner persisted and validation only for that candidate. Update guide and safely reload idle service.

## Completion evidence (2026-09-16)

- Targeted Python checks: 25 passed (studies, jobs, web, experiments).
- Frontend checks: 16 passed (studies, research), including a browser-bootstrap regression caught during acceptance and fixed by deferred callback lookup.
- Real browser sample group `41f97cf6f57f4b2691b1e125a277d5b1`: three earlier candidates, single later validation, persisted history and mobile width verified.
- Real MLflow store: four FINISHED runs, three selection and one validation; locked holding-period parameter matches group.
- Guide updated. Synthetic sample evidence verifies orchestration only, not investment performance.
