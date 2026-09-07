from __future__ import annotations

import argparse
import json
from datetime import date
from dataclasses import asdict
import hashlib
import pandas as pd
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
    from .registry import build_strategy
    params = config.strategy.parameters
    if config.strategy.name == "fixed_asset": strategy = build_strategy('fixed_asset', {'symbol':params.get('symbol','588000.SH')})
    elif config.strategy.name in {"cross_sectional_rank", "rank"}:
        strategy = build_strategy('cross_sectional_rank', {key: value for key, value in params.items() if key != "symbol"})
    else: raise ValueError(f"unknown strategy: {config.strategy.name}")
    # Recommendation uses the same point-in-time market trigger as backtest.
    strategy.index_symbol = config.market.index_symbol
    strategy.trigger_level = config.market.trigger_level
    strategy.trigger_return_threshold = config.market.trigger_return_threshold
    strategy.min_declining_count = config.market.min_declining_count
    return strategy


def _load(config_path):
    config = load_config(config_path)
    path = Path(config.metadata.get("data_path_resolved", config.data.path))
    data = CsvMarketDataProvider(path).load()
    if config.market.min_declining_count is not None and not config.market.breadth_path:
        raise ValueError("historical market breadth requires a validated [market].breadth_path with counts and source")
    if config.market.breadth_path:
        from .breadth import load_breadth, attach_breadth
        breadth_path = Path(config.market.breadth_path)
        if not breadth_path.is_absolute():
            breadth_path = Path(config_path).resolve().parent / breadth_path
        breadth = load_breadth(breadth_path)
        data = attach_breadth(data, breadth, config.market.index_symbol)
        config.metadata["breadth_source"] = sorted(breadth.source.unique().tolist())
        config.metadata["breadth_sha256"] = hashlib.sha256(breadth_path.read_bytes()).hexdigest()
    if config.market.min_declining_count is not None:
        index = data[data.symbol == config.market.index_symbol]
        if "declining_count" not in index or index.declining_count.notna().sum() == 0:
            raise ValueError("historical market breadth is required; configure [market].breadth_path")
        missing_breadth = int(index.declining_count.isna().sum())
        config.metadata["breadth_coverage"] = {"index_sessions": len(index), "missing_sessions": missing_breadth}
        if missing_breadth:
            config.metadata.setdefault("warnings", []).append(
                f"data quality: market breadth missing on {missing_breadth} sessions; results cover only observed signals.")
    else:
        config.metadata.setdefault("warnings", []).append("Legacy index-level trigger: this is NOT the 4000 declining stocks strategy.")
    config.metadata["data_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return config, data


def _engine(config):
    return BacktestEngine(initial_cash=config.backtest.initial_cash,
        holding_period_days=config.backtest.holding_period_days,
        commission_rate=config.costs.commission_rate, stamp_duty_rate=config.costs.stamp_duty_rate,
        minimum_commission=config.costs.minimum_commission, slippage_bps=config.costs.slippage_bps,
        index_symbol=config.market.index_symbol, trigger_level=config.market.trigger_level,
        trigger_return_threshold=config.market.trigger_return_threshold,
        min_declining_count=config.market.min_declining_count, lot_size=config.backtest.lot_size)


def _metadata(config):
    return dict(config.metadata) | {"source": config.metadata.get("source", config.data.source),
        "adjustment": config.data.adjustment, "costs": asdict(config.costs),
        "market": asdict(config.market), "strategy": asdict(config.strategy),
        "backtest": asdict(config.backtest),
        "execution": "D close signal; D+1 open entry; exit after holding_period_days at open"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="strategy", description="Offline A-share strategy research tool")
    sub = parser.add_subparsers(dest="command", required=True)
    web = sub.add_parser('serve', help='Start the local browser workbench')
    web.add_argument('--port', type=int, default=8765)
    web.add_argument('--project-root', default=str(Path(__file__).resolve().parents[2]))
    market_download = sub.add_parser('download-market', help='Download Tencent index and ETF daily bars')
    market_download.add_argument('--start', required=True)
    market_download.add_argument('--end', required=True)
    market_download.add_argument('--output', default='data/real')
    market_download.add_argument('--symbols', nargs='+')
    market_download.add_argument('--adjustment', choices=['none','qfq'], default='none')
    back = sub.add_parser("backtest"); back.add_argument("--config", required=True); back.add_argument("--output", default="reports")
    rec = sub.add_parser("recommend"); rec.add_argument("--config", required=True); rec.add_argument("--as-of", required=True)
    comp = sub.add_parser("compare"); comp.add_argument("--config", required=True); comp.add_argument("--output", default="reports/mvp")
    download = sub.add_parser("download-breadth", help="Download full-market daily data using TUSHARE_TOKEN")
    download.add_argument("--start", required=True)
    download.add_argument("--end", required=True)
    download.add_argument("--output", default="data/real")
    ingest = sub.add_parser("import-breadth", help="Aggregate an exported full-market daily CSV")
    ingest.add_argument("--input", required=True)
    ingest.add_argument("--source", required=True)
    ingest.add_argument("--output", default="data/real/breadth.csv")
    args = parser.parse_args(argv)
    try:
        if args.command == 'serve':
            from .web import serve
            serve(Path(args.project_root), args.port)
            return 0
        if args.command == 'download-market':
            from .market_download import download_market
            print(json.dumps(download_market(args.start,args.end,args.output,args.symbols,args.adjustment)))
            return 0
        if args.command == "download-breadth":
            from .ingest import download_tushare_daily
            paths = download_tushare_daily(args.start, args.end, args.output)
            print(json.dumps(paths, default=str))
            return 0
        if args.command == "import-breadth":
            from .ingest import build_breadth
            frame = pd.read_csv(args.input, dtype={"trade_date": str, "ts_code": str})
            breadth = build_breadth(frame, args.source)
            if breadth.empty:
                raise ValueError("no market breadth rows in input")
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            breadth.to_csv(output, index=False)
            print(json.dumps({"breadth": str(output.resolve()), "dates": len(breadth),
                              "warning": "Minimum row count does not prove full-market coverage; audit source and exchange coverage."}))
            return 0
        config, data = _load(args.config)
        if args.command == "compare":
            from .comparison import compare
            payload = compare(config, data, args.output)
            print(json.dumps({"output": str(Path(args.output).resolve()), "files": payload.get("files"), "warnings": payload.get("warnings")}, default=str))
            return 0
        strategy = _strategy(config)
        if args.command == "recommend":
            payload = recommend(date.fromisoformat(args.as_of), data, strategy).to_dict()
            payload["metadata"] = _metadata(config)
            payload["warnings"] = list(dict.fromkeys(payload["warnings"] + config.metadata.get("warnings", [])))
            print(json.dumps(payload, indent=2, default=str))
            return 0
        result = _engine(config).run(data, strategy); metrics = evaluate(result)
        paths = write_report(result, metrics, args.output, metadata=_metadata(config))
        pd.DataFrame(result.events).to_csv(Path(args.output) / "events.csv", index=False)
        report_warnings = json.loads(paths.summary.read_text(encoding="utf-8")).get("warnings", result.warnings)
        print(json.dumps({"output": str(Path(args.output).resolve()), "files": [str(p) for p in paths], "warnings": report_warnings}))
        return 0
    except Exception as exc:
        parser.error(str(exc)); return 2
