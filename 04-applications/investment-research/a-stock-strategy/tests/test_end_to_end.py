"""End-to-end acceptance tests for the offline A-share workflow."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from strategy.backtest import BacktestEngine
from strategy.config import load_config
from strategy.data import CsvMarketDataProvider
from strategy.evaluation import evaluate
from strategy.recommendation import recommend
from strategy.strategies.fixed import FixedAssetStrategy
from strategy.strategies.rank import CrossSectionalRankStrategy


PROJECT = Path(__file__).parents[1]
DATA = PROJECT / "data" / "sample" / "market.csv"


def _engine(config):
    return BacktestEngine(
        initial_cash=config.backtest.initial_cash,
        holding_period_days=config.backtest.holding_period_days,
        commission_rate=config.costs.commission_rate,
        stamp_duty_rate=config.costs.stamp_duty_rate,
        minimum_commission=config.costs.minimum_commission,
        slippage_bps=config.costs.slippage_bps,
        index_symbol=config.market.index_symbol,
        trigger_level=config.market.trigger_level,
        trigger_return_threshold=config.market.trigger_return_threshold,
    )


def _write_dynamic_config(tmp_path: Path) -> Path:
    path = tmp_path / "dynamic.toml"
    path.write_text(
        f'''[data]\nsource = "local-fixture"\npath = "{DATA}"\nformat = "csv"\nadjustment = "none"\n\n'''
        '''[strategy]\nname = "cross_sectional_rank"\n[strategy.parameters]\n'''
        '''candidate_symbols = ["588000.SH", "600000.SH"]\n'''
        '''momentum_window = 1\nreversal_window = 1\nvolatility_window = 1\nvolume_window = 1\n'''
        '''weights = { momentum = 1.0, reversal = 0.0, volatility = 0.0, volume = 0.0 }\n\n'''
        '''[backtest]\ninitial_cash = 100000.0\nholding_period_days = 1\n\n'''
        '''[market]\nindex_symbol = "000001.SH"\ntrigger_level = 4000.0\ntrigger_return_threshold = 0.0\n\n'''
        '''[costs]\ncommission_rate = 0.0003\nstamp_duty_rate = 0.001\nminimum_commission = 5.0\nslippage_bps = 2.0\n\n'''
        '''[metadata]\nsource = "local-fixture"\nadjustment_note = "unadjusted"\n''',
        encoding="utf-8",
    )
    return path


def _assert_report(paths) -> dict:
    output = paths if isinstance(paths, Path) else paths.summary.parent
    expected = {"trades.csv", "equity.csv", "summary.json", "report.png"}
    assert {item.name for item in output.iterdir()} >= expected
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["data_range"]["start"]
    assert summary["data_range"]["end"]
    assert summary["adjustment"] == "none"
    assert set((summary["costs"] or {})) >= {"commission_rate", "stamp_duty_rate", "slippage_bps"}
    assert summary["generated_at"]
    assert (output / "report.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    return summary


def test_fixed_and_dynamic_backtests_have_comparable_metrics_and_reports(tmp_path):
    config = load_config(PROJECT / "configs" / "baseline.toml")
    data = CsvMarketDataProvider(DATA).load()
    fixed = _engine(config).run(data, FixedAssetStrategy(config.strategy.parameters["symbol"]))
    dynamic = CrossSectionalRankStrategy(
        candidate_symbols=["588000.SH", "600000.SH"],
        momentum_window=1,
        reversal_window=1,
        volatility_window=1,
        volume_window=1,
        weights={"momentum": 1.0},
    )
    dynamic_result = _engine(config).run(data, dynamic)

    fixed_metrics = evaluate(fixed)
    dynamic_metrics = evaluate(dynamic_result, benchmark_equity=fixed.equity)
    assert fixed_metrics.trade_count >= 1
    assert dynamic_metrics.trade_count >= 1
    assert dynamic_metrics.benchmark_return is not None
    assert dynamic_metrics.excess_return is not None
    assert fixed_metrics.cumulative_return == evaluate(fixed).cumulative_return

    from strategy.reporting import write_report

    costs = asdict(config.costs)
    _assert_report(write_report(fixed, fixed_metrics, tmp_path / "fixed", metadata={"source": "local-fixture", "adjustment": "none", "costs": costs}))
    _assert_report(write_report(dynamic_result, dynamic_metrics, tmp_path / "dynamic", metadata={"source": "local-fixture", "adjustment": "none", "costs": costs}))


def test_recommendation_choice_matches_dynamic_strategy_as_of_and_cli_is_offline(tmp_path):
    config_path = _write_dynamic_config(tmp_path)
    config = load_config(config_path)
    data = CsvMarketDataProvider(DATA).load()
    strategy = CrossSectionalRankStrategy(**config.strategy.parameters)
    strategy.index_symbol = config.market.index_symbol
    strategy.trigger_level = config.market.trigger_level
    strategy.trigger_return_threshold = config.market.trigger_return_threshold
    as_of = data["date"].dt.date.unique()[2]
    recommendation = recommend(as_of, data, strategy)
    assert recommendation.selected is not None
    assert recommendation.selected.symbol == recommendation.rankings[0]["symbol"]

    output = tmp_path / "cli-report"
    backtest = subprocess.run(
        ["uv", "run", "--offline", "--project", str(PROJECT), "python", "-m", "strategy", "backtest", "--config", str(config_path), "--output", str(output)],
        cwd=Path("/tmp"), capture_output=True, text=True,
    )
    assert backtest.returncode == 0, backtest.stderr
    _assert_report(output)
    rec = subprocess.run(
        ["uv", "run", "--offline", "--project", str(PROJECT), "python", "-m", "strategy", "recommend", "--config", str(config_path), "--as-of", as_of.isoformat()],
        cwd=Path("/tmp"), capture_output=True, text=True,
    )
    assert rec.returncode == 0, rec.stderr
    payload = json.loads(rec.stdout)
    assert payload["selected"]["symbol"] == recommendation.selected.symbol
    assert "research" in payload["disclaimer"].lower()
