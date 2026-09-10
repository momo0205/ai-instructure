from __future__ import annotations
import argparse
import json
from datetime import date
from pathlib import Path
import pandas as pd
from strategy.application.legacy_config import (
    build_legacy_strategy as _strategy, load_inputs as _load,
    make_engine as _engine, metadata as _metadata, execute_config,
)
from strategy.application.recommendation import recommend


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="strategy", description="Offline A-share strategy research tool")
    sub = parser.add_subparsers(dest="command", required=True)
    web = sub.add_parser('serve', help='Start the local browser workbench')
    web.add_argument('--port', type=int, default=8765)
    web.add_argument('--project-root', default=str(Path(__file__).resolve().parents[4]))
    market_download = sub.add_parser('download-market', help='Download Tencent index and ETF daily bars')
    market_download.add_argument('--start', required=True)
    market_download.add_argument('--end', required=True)
    market_download.add_argument('--output', default='data/real')
    market_download.add_argument('--symbols', nargs='+')
    market_download.add_argument('--adjustment', choices=['none','qfq'], default='none')
    back = sub.add_parser("backtest")
    input_group = back.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--config', help='Legacy TOML configuration')
    input_group.add_argument('--request', help='Workbench JSON request, same contract as Web API')
    back.add_argument('--project-root', default=str(Path(__file__).resolve().parents[4]))
    back.add_argument('--output', default='reports')
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
            from strategy.interfaces.web.server import serve
            serve(Path(args.project_root), args.port)
            return 0
        if args.command == 'download-market':
            from strategy.market_data.tencent import download_market
            print(json.dumps(download_market(args.start,args.end,args.output,args.symbols,args.adjustment)))
            return 0
        if args.command == "download-breadth":
            from strategy.market_data.ingest import download_tushare_daily
            paths = download_tushare_daily(args.start, args.end, args.output)
            print(json.dumps(paths, default=str))
            return 0
        if args.command == "import-breadth":
            from strategy.market_data.ingest import build_breadth
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
        if args.command == 'backtest' and args.request:
            from strategy.application.backtests import execute
            request = json.loads(Path(args.request).read_text())
            result = execute(Path(args.project_root), request, args.output)
            print(json.dumps({'output': str(Path(args.output).resolve()),
                              'files': [str(Path(args.output)/'result.json')], 'warnings': result['warnings']}))
            return 0
        config, data = _load(args.config)
        if args.command == "compare":
            from strategy.application.comparison import compare
            payload = compare(config, data, args.output)
            print(json.dumps({"output": str(Path(args.output).resolve()), "files": payload.get("files"), "warnings": payload.get("warnings")}, default=str))
            return 0
        if args.command == "recommend":
            strategy = _strategy(config)
            payload = recommend(date.fromisoformat(args.as_of), data, strategy).to_dict()
            payload["metadata"] = _metadata(config)
            payload["warnings"] = list(dict.fromkeys(payload["warnings"] + config.metadata.get("warnings", [])))
            print(json.dumps(payload, indent=2, default=str))
            return 0
        print(json.dumps(execute_config(config, data, args.output)))
        return 0
    except Exception as exc:
        parser.error(str(exc)); return 2
