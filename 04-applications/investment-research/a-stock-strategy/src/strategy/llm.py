"""Optional, explanation-only language model boundary.

The deterministic strategy never depends on this module's network adapter.  A
provider is selected explicitly; the default is a local no-op implementation.
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    def explain_recommendation(self, result: Any) -> str: ...
    def summarize_backtest(self, report: Any) -> str: ...


class NoopLLMProvider:
    enabled = False
    name = "noop"
    model = None

    def explain_recommendation(self, result: Any) -> str:
        return ""

    def summarize_backtest(self, report: Any) -> str:
        return ""


@dataclass(slots=True)
class BacktestReport:
    """Detached input supplied to providers, so provider code cannot alter results."""

    trades: list[Any]
    equity: list[Any]
    metrics: Any
    warnings: list[str]


class OpenAICompatibleLLMProvider:
    enabled = True
    name = "openai-compatible"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini",
                 base_url: str = "https://api.openai.com/v1/chat/completions"):
        if not api_key:
            raise ValueError("api_key is required when enabling an LLM provider")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def explain_recommendation(self, result: Any) -> str:
        return self._complete("Explain this research recommendation; do not give trading instructions.", result)

    def summarize_backtest(self, report: Any) -> str:
        return self._complete("Summarize these deterministic backtest results; do not alter any values.", report)

    def _complete(self, instruction: str, value: Any) -> str:
        from urllib.request import Request, urlopen

        body = {"model": self.model, "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": json.dumps(_jsonable(value), ensure_ascii=False)},
        ], "temperature": 0}
        request = Request(self.base_url, data=json.dumps(body).encode(), headers={
            "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=30) as response:  # noqa: S310 - explicitly configured endpoint
            payload = json.load(response)
        return str(payload["choices"][0]["message"]["content"])


def get_llm_provider(environ: dict[str, str] | None = None) -> LLMProvider:
    """Return a provider only when explicitly enabled and configured."""
    env = os.environ if environ is None else environ
    if env.get("LLM_PROVIDER", "").lower() != "openai":
        return NoopLLMProvider()
    key = env.get("OPENAI_API_KEY", "")
    if not key:
        return NoopLLMProvider()
    return OpenAICompatibleLLMProvider(key, env.get("LLM_MODEL", "gpt-4o-mini"),
                                       env.get("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"))


def _jsonable(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def detached(value: Any) -> Any:
    """Make a provider input independent from deterministic result objects."""
    return deepcopy(value)
