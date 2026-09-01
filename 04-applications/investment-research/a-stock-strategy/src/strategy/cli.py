from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .backtest import BacktestEngine
from .config import load_config
from .data import CsvMarketDataProvider
from .evaluation import evaluate
from .recommendation import recommend
from .reporting import write_report
from .strategies.fixed import FixedAssetStrategy
from .strategies.rank import CrossSectionalRankStrategy


def _strategy(config):
    params = config.strategy.parameters
    if config.strategy.name == "fixed_asset": strategy = FixedAssetStrategy(params.get("symbol", "588000.SH"))
    elif config.strategy.name in {"cross_sectional_rank", "rank"}: strategy = CrossSectionalRankStrategy(**params)
    else: raise ValueError(f"unknown strategy: {config.strategy.name}")
    # Recommendation uses the same point-in-time market trigger as backtest.
    strategy.index_symbol = config.market.index_symbol
    strategy.trigger_level = config.market.trigger_level
    strategy.trigger_return_threshold = config.market.trigger_return_threshold
    return strategy


def _load(config_path):
    config = load_config(config_path)
    path = Path(config.metadata.get("data_path_resolved", config.data.path))
    return config, CsvMarketDataProvider(path).load()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="strategy", description="Offline A-share strategy research tool")
    sub = parser.add_subparsers(dest="command", required=True)
    back = sub.add_parser("backtest"); back.add_argument("--config", required=True); back.add_argument("--output", default="reports")
    rec = sub.add_parser("recommend"); rec.add_argument("--config", required=True); rec.add_argument("--as-of", required=True)
    args = parser.parse_args(argv)
    try:
        config, data = _load(args.config); strategy = _strategy(config)
        if args.command == "recommend":
            print(json.dumps(recommend(date.fromisoformat(args.as_of), data, strategy).to_dict(), indent=2, default=str))
            return 0
        engine = BacktestEngine(initial_cash=config.backtest.initial_cash, holding_period_days=config.backtest.holding_period_days,
            commission_rate=config.costs.commission_rate, stamp_duty_rate=config.costs.stamp_duty_rate,
            minimum_commission=config.costs.minimum_commission, slippage_bps=config.costs.slippage_bps,
            index_symbol=config.market.index_symbol, trigger_level=config.market.trigger_level,
            trigger_return_threshold=config.market.trigger_return_threshold)
        result = engine.run(data, strategy); metrics = evaluate(result)
        paths = write_report(result, metrics, args.output, metadata={"source": config.metadata.get("source", config.data.source), "data_path": config.metadata.get("data_path_resolved", config.data.path), "adjustment": config.data.adjustment, "costs": {"commission_rate": config.costs.commission_rate, "stamp_duty_rate": config.costs.stamp_duty_rate, "minimum_commission": config.costs.minimum_commission, "slippage_bps": config.costs.slippage_bps}})
        report_warnings = json.loads(paths.summary.read_text(encoding="utf-8")).get("warnings", result.warnings)
        print(json.dumps({"output": str(Path(args.output).resolve()), "files": [str(p) for p in paths], "warnings": report_warnings}))
        return 0
    except Exception as exc:
        parser.error(str(exc)); return 2
