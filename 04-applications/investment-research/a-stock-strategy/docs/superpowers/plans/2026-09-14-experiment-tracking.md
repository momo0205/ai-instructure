# Experiment Tracking Implementation Plan

> **For agentic workers:** Use executing-plans and test-driven-development; UI is delegated independently and reviewed with backend integration.

**Goal:** Persist successful workbench backtests to isolated MLflow and expose sync state/retry.

**Architecture:** A separate export queue and atomic per-task state files keep tracking independent of calculation. A subprocess runs a stdlib entry point with the configured Python interpreter and lazy MLflow import. Local SQLite and artifact roots are fixed by server state directory.

**Tech Stack:** Python threading/subprocess/JSON, MLflow client in separate env, existing HTTP and JS.

1. Add tests/test_experiments.py: fake exporter failure/retry, queue deduplication, restart recovery, disabled state; JobManager test automatic enqueue. Run `.venv/bin/pytest tests/test_experiments.py -q` and observe missing module failure.
2. Add application/experiments.py: ExperimentManager owns state and queue; enqueue(job) accepts succeeded only, view(id), close(). Export calls subprocess with 60s timeout; failures leave original job untouched. Atomic JSON replaces prevent partial reads.
3. Add storage/mlflow_export.py: executable receives state/run folder/job ID; uses MlflowClient, stable experiment and job tag, run ID checkpoint, explicit artifact/result and flattened numeric metrics. No global autologging or credentials in artifacts.
4. Integrate JobManager optional experiment_python/ui_url config; queue after successful transition; show experiment in task views; add GET /api/experiments and POST /api/jobs/{id}/experiment. CLI serve flags pass configuration.
5. UI task status/retry/link with targeted Node tests (delegated). Verify existing job/web boundaries and actual isolated MLflow sample run, retry returns same run, query back metrics/artifacts.
6. Document setup/start/limitations; review diff and checks. Restart local service only after verifying no active work.
