"""旧TOML适配器：保留历史触发、份额、成本和报告语义，统一交给运行服务。"""
from pathlib import Path
from dataclasses import asdict
import hashlib
import json
import pandas as pd
from strategy.application.configuration import load_config
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.application import simulation
from strategy.backtesting.engine import BacktestEngine
from strategy.storage.reports import write_report


def build_legacy_strategy(config):
    from strategy.strategies.registry import build_strategy
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


def load_inputs(config_path):
    config = load_config(config_path)
    path = Path(config.metadata.get("data_path_resolved", config.data.path))
    data = CsvMarketDataProvider(path).load()
    if config.market.min_declining_count is not None and not config.market.breadth_path:
        raise ValueError("historical market breadth requires a validated [market].breadth_path with counts and source")
    if config.market.breadth_path:
        from strategy.market_data.breadth import load_breadth, attach_breadth
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


def engine_options(config):
    return dict(initial_cash=config.backtest.initial_cash,
        holding_period_days=config.backtest.holding_period_days,
        commission_rate=config.costs.commission_rate, stamp_duty_rate=config.costs.stamp_duty_rate,
        minimum_commission=config.costs.minimum_commission, slippage_bps=config.costs.slippage_bps,
        index_symbol=config.market.index_symbol, trigger_level=config.market.trigger_level,
        trigger_return_threshold=config.market.trigger_return_threshold,
        min_declining_count=config.market.min_declining_count, lot_size=config.backtest.lot_size)


def metadata(config):
    return dict(config.metadata) | {"source": config.metadata.get("source", config.data.source),
        "adjustment": config.data.adjustment, "costs": asdict(config.costs),
        "market": asdict(config.market), "strategy": asdict(config.strategy),
        "backtest": asdict(config.backtest),
        "execution": "D close signal; D+1 open entry; exit after holding_period_days at open"}


def make_engine(config):
    """兼容旧Python辅助入口；正式执行使用SimulationPlan。"""
    return BacktestEngine(**engine_options(config))


def plan_for_config(config, data, strategy=None):
    return simulation.SimulationPlan(data, strategy if strategy is not None else build_legacy_strategy(config),
                                     engine_options(config), profile='legacy_toml')


def execute_config(config, data, output_dir):
    outcome = simulation.run_simulation(plan_for_config(config, data))
    report_metadata = metadata(config) | {'configuration_profile': 'legacy_toml'}
    paths = write_report(outcome.result, outcome.metrics, output_dir, metadata=report_metadata)
    pd.DataFrame(outcome.result.events).to_csv(Path(output_dir)/'events.csv', index=False)
    warnings = json.loads(paths.summary.read_text(encoding='utf-8')).get('warnings', outcome.result.warnings)
    return {'output': str(Path(output_dir).resolve()), 'files': [str(p) for p in paths], 'warnings': warnings}
