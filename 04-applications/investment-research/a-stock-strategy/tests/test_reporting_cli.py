from datetime import date
import json
import struct
import subprocess
import sys

import pandas as pd

from strategy.backtest import BacktestEngine
from strategy.evaluation import evaluate
from strategy.reporting import write_report
from strategy.strategies.fixed import FixedAssetStrategy


def _bars():
    return pd.DataFrame([
        {"date": "2026-08-01", "symbol": "000001.SH", "open": 4000, "high": 4010, "low": 3990, "close": 4005, "volume": 1, "amount": 1, "is_suspended": False, "limit_up": False, "limit_down": False},
        {"date": "2026-08-01", "symbol": "588000.SH", "open": 1, "high": 1.1, "low": .9, "close": 1.02, "volume": 1, "amount": 1, "is_suspended": False, "limit_up": False, "limit_down": False},
        {"date": "2026-08-02", "symbol": "000001.SH", "open": 4005, "high": 4010, "low": 3995, "close": 4010, "volume": 1, "amount": 1, "is_suspended": False, "limit_up": False, "limit_down": False},
        {"date": "2026-08-02", "symbol": "588000.SH", "open": 1.02, "high": 1.1, "low": 1, "close": 1.06, "volume": 1, "amount": 1, "is_suspended": False, "limit_up": False, "limit_down": False},
    ])


def test_write_report_serializes_all_artifacts(tmp_path):
    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0,
                            minimum_commission=0, slippage_bps=0).run(_bars(), FixedAssetStrategy())
    paths = write_report(result, evaluate(result), tmp_path,
                         metadata={"data_source": "fixture", "adjustment": "none", "costs": {}})
    assert {p.name for p in paths} == {"trades.csv", "equity.csv", "summary.json", "report.png"}
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert all(warning in summary["warnings"] for warning in result.warnings)
    assert summary["metadata"]["source"] == "fixture"
    assert summary["metadata"]["adjustment"] == "none"
    assert "range" in summary["metadata"] and "costs" in summary["metadata"]
    png = (tmp_path / "report.png").read_bytes()
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", png[16:24])
    assert width >= 1 and height >= 1
    if width == height == 1:
        assert any("matplotlib" in warning for warning in summary["warnings"])
    assert list(pd.read_csv(tmp_path / "equity.csv").columns) == ["date", "cash", "position_value", "equity", "drawdown"]


def test_report_without_metadata_emits_explicit_contract_keys(tmp_path):
    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0,
                            minimum_commission=0, slippage_bps=0).run(_bars(), FixedAssetStrategy())
    write_report(result, evaluate(result), tmp_path)
    metadata = json.loads((tmp_path / "summary.json").read_text())["metadata"]
    assert metadata["source"] == "unknown"
    assert metadata["adjustment"] == "unknown"
    assert metadata["range"]["start"] == "2026-08-01"
    assert "costs" in metadata


def test_recommendation_reports_non_trigger_and_data_quality_reasons():
    from strategy.recommendation import recommend
    data = _bars().query("symbol == '588000.SH'")
    result = recommend(date(2026, 8, 1), data, FixedAssetStrategy())
    assert result.warnings
    assert any("index" in warning.lower() for warning in result.warnings)


def test_recommendation_rejects_malformed_or_missing_index():
    from strategy.recommendation import recommend
    malformed = _bars()
    malformed["close"] = malformed["close"].astype(object)
    malformed.loc[(malformed.symbol == "000001.SH") & (malformed.date == "2026-08-01"), "close"] = "bad"
    result = recommend(date(2026, 8, 1), malformed, FixedAssetStrategy())
    assert result.triggered is False
    assert result.selected is None
    assert any("index" in warning.lower() for warning in result.warnings)


def test_recommendation_rejects_nonfinite_index_close():
    from strategy.recommendation import recommend
    malformed = _bars()
    malformed["close"] = malformed["close"].astype(object)
    malformed.loc[(malformed.symbol == "000001.SH") & (malformed.date == "2026-08-01"), "close"] = float("inf")
    result = recommend(date(2026, 8, 1), malformed, FixedAssetStrategy())
    assert result.triggered is False and result.selected is None
    assert any("invalid market index" in warning.lower() for warning in result.warnings)


def test_recommendation_ignores_future_data_quality_errors():
    from strategy.recommendation import recommend
    malformed = _bars()
    malformed["close"] = malformed["close"].astype(object)
    malformed.loc[malformed["date"] == "2026-08-02", "close"] = "bad"
    result = recommend(date(2026, 8, 1), malformed, FixedAssetStrategy())
    assert not any("invalid close" in warning.lower() for warning in result.warnings)


def test_recommendation_is_independent_of_input_order():
    from strategy.recommendation import recommend
    ordered = _bars()
    shuffled = ordered.iloc[::-1].reset_index(drop=True)
    first = recommend(date(2026, 8, 1), ordered, FixedAssetStrategy())
    second = recommend(date(2026, 8, 1), shuffled, FixedAssetStrategy())
    assert first.to_dict() == second.to_dict()


def test_report_merges_metadata_warnings(tmp_path):
    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0,
                            minimum_commission=0, slippage_bps=0).run(_bars(), FixedAssetStrategy())
    write_report(result, evaluate(result), tmp_path, metadata={"warnings": ["caller warning"]})
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert "caller warning" in summary["metadata"]["warnings"]


def test_cli_backtest_and_recommend_commands(tmp_path):
    root = __import__("pathlib").Path(__file__).parents[1]
    out = tmp_path / "out"
    cmd = [sys.executable, "-m", "strategy", "backtest", "--config", "configs/baseline.toml", "--output", str(out)]
    backtest = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert backtest.returncode == 0, backtest.stderr
    assert (out / "summary.json").exists()
    rec = subprocess.run([sys.executable, "-m", "strategy", "recommend", "--config", "configs/baseline.toml", "--as-of", "2026-08-01"], cwd=root, capture_output=True, text=True)
    assert rec.returncode == 0, rec.stderr
    payload = json.loads(rec.stdout)
    assert payload["as_of"] == "2026-08-01"
    assert "triggered" in payload and "research" in payload["disclaimer"].lower()
