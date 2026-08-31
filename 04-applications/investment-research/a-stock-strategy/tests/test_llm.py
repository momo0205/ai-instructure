import json
from datetime import date

import pandas as pd

from strategy.backtest import BacktestEngine
from strategy.domain import EquityPoint, Selection, Trade
from strategy.evaluation import evaluate
from strategy.llm import BacktestReport, LLMProvider, NoopLLMProvider, _jsonable, get_llm_provider
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


def test_jsonable_recursively_serializes_domain_dataclasses_and_nested_dates():
    trade = Trade(date(2026, 8, 1), date(2026, 8, 2), None, "000001.SH", 10, 4_000, None)
    point = EquityPoint(date(2026, 8, 2), 900, 100, 1_000, -0.02)
    selection = Selection("000001.SH", 0.8, {"as_of": date(2026, 8, 2), "points": [point]})
    report = BacktestReport([trade], [point], selection, ["warning"])

    payload = _jsonable(report)

    assert payload == {
        "trades": [{
            "signal_date": "2026-08-01",
            "entry_date": "2026-08-02",
            "exit_date": None,
            "symbol": "000001.SH",
            "quantity": 10,
            "entry_price": 4000,
            "exit_price": None,
            "fees": 0.0,
            "pnl": 0.0,
            "exit_reason": "",
        }],
        "equity": [{
            "date": "2026-08-02",
            "cash": 900,
            "position_value": 100,
            "equity": 1000,
            "drawdown": -0.02,
        }],
        "metrics": {
            "symbol": "000001.SH",
            "score": 0.8,
            "features": {
                "as_of": "2026-08-02",
                "points": [{
                    "date": "2026-08-02",
                    "cash": 900,
                    "position_value": 100,
                    "equity": 1000,
                    "drawdown": -0.02,
                }],
            },
            "reason": "",
        },
        "warnings": ["warning"],
    }
    json.dumps(payload)


def test_actual_llm_metadata_cannot_be_suppressed_by_caller_metadata(tmp_path):
    result = BacktestEngine(1000, commission_rate=0, stamp_duty_rate=0, minimum_commission=0).run(_bars(), FixedAssetStrategy())
    metrics = evaluate(result)

    class Provider:
        enabled = True
        name = "test-provider"
        model = "test-model"

        def explain_recommendation(self, recommendation):
            return ""

        def summarize_backtest(self, report):
            return ""

    write_report(result, metrics, tmp_path, metadata={"llm": {"enabled": False, "status": "disabled"}}, llm_provider=Provider())

    llm_metadata = json.loads((tmp_path / "summary.json").read_text())["metadata"]["llm"]
    assert llm_metadata["enabled"] is True
    assert llm_metadata["status"] == "enabled"
    assert llm_metadata["provider"] == "test-provider"


def test_failing_llm_provider_does_not_block_deterministic_report(tmp_path):
    result = BacktestEngine(1000, commission_rate=0, stamp_duty_rate=0, minimum_commission=0).run(_bars(), FixedAssetStrategy())
    metrics = evaluate(result)

    class FailingProvider:
        enabled = True
        name = "failing-provider"

        def explain_recommendation(self, recommendation):
            raise OSError("network unavailable")

        def summarize_backtest(self, report):
            raise TypeError("cannot serialize provider payload")

    paths = write_report(result, metrics, tmp_path, llm_provider=FailingProvider())
    payload = json.loads(paths.summary.read_text())
    assert payload["metrics"]["trade_count"] == metrics.trade_count
    assert payload["metadata"]["llm"]["status"] == "error"
    assert any("llm" in warning.lower() for warning in payload["warnings"])
