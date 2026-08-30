# Task 6 Report: Optional LLM Explanation Provider

## Status

Implemented and verified.

## Delivered

- Added `strategy.llm.LLMProvider`, `NoopLLMProvider`, `BacktestReport`, and an OpenAI-compatible adapter.
- The default provider is a no-op with no environment, dependency, network, or API-key requirement.
- `get_llm_provider` enables the adapter only when `LLM_PROVIDER=openai` and `OPENAI_API_KEY` are explicitly configured; HTTP code is called only by the adapter.
- `write_report` records LLM enabled/disabled status, provider, model (when enabled), prompt summary, and generation time. Explanations are metadata only.
- Provider inputs are deep-copied, so provider code/output cannot mutate deterministic trades, metrics, or equity data.

## Verification

```text
uv run pytest tests/test_llm.py -q: 3 passed
uv run pytest -q: 45 passed
```

## Concerns

- The adapter uses Python's standard-library HTTP client and is intentionally not invoked by default; no live API call was made in tests.
