import json
from datetime import date

import pandas as pd

from strategy.backtest import BacktestEngine
from strategy.evaluation import evaluate
from strategy.llm import LLMProvider, NoopLLMProvider, get_llm_provider
from strategy.reporting import write_report
from strategy.strategies.fixed import FixedAssetStrategy


def _bars():
    return pd.DataFrame([
        {"date": "2026-08-01", "symbol": "000001.SH", "open": 4000, "high": 4010, "low": 3990, "close": 4005, "volume": 1, "amount": 1},
        {"date": "2026-08-02", "symbol": "000001.SH", "open": 4005, "high": 4010, "low": 3995, "close": 4010, "volume": 1, "amount": 1},
    ])


def test_noop_provider_works_without_environment(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = get_llm_provider()
    assert isinstance(provider, NoopLLMProvider)
    assert provider.explain_recommendation(None) == ""
    assert provider.summarize_backtest(None) == ""


def test_report_records_llm_disabled_status_without_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = BacktestEngine(1000, commission_rate=0, stamp_duty_rate=0, minimum_commission=0).run(_bars(), FixedAssetStrategy())
    write_report(result, evaluate(result), tmp_path)
    metadata = json.loads((tmp_path / "summary.json").read_text())["metadata"]
    assert metadata["llm"]["enabled"] is False
    assert metadata["llm"]["status"] == "disabled"


def test_provider_output_cannot_mutate_metrics_or_trades(tmp_path):
    result = BacktestEngine(1000, commission_rate=0, stamp_duty_rate=0, minimum_commission=0).run(_bars(), FixedAssetStrategy())
    metrics = evaluate(result)
    original_trades = list(result.trades)
    original_metrics = metrics

    class MutatingProvider:
        def explain_recommendation(self, recommendation):
            return "explanation"

        def summarize_backtest(self, report):
            report.trades.clear()
            report.metrics = None
            return "summary"

    write_report(result, metrics, tmp_path, llm_provider=MutatingProvider())
    assert result.trades == original_trades
    assert metrics == original_metrics
    payload = json.loads((tmp_path / "summary.json").read_text())
    assert payload["metrics"]["trade_count"] == len(original_trades)
    assert payload["metadata"]["llm"]["summary"] == "summary"
