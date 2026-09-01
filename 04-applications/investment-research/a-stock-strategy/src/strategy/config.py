from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib


@dataclass(frozen=True, slots=True)
class DataConfig:
    source: str
    path: str
    format: str = "csv"
    adjustment: str = "none"


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    name: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BacktestSettings:
    initial_cash: float
    holding_period_days: int = 1
    commission_rate: float = 0.0003
    stamp_duty_rate: float = 0.001
    minimum_commission: float = 5.0
    slippage_bps: float = 2.0


@dataclass(frozen=True, slots=True)
class MarketConfig:
    index_symbol: str = "000001.SH"
    trigger_level: float = 4000.0
    trigger_return_threshold: float = 0.0


@dataclass(frozen=True, slots=True)
class CostConfig:
    commission_rate: float = 0.0003
    stamp_duty_rate: float = 0.001
    minimum_commission: float = 5.0
    slippage_bps: float = 2.0


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    data: DataConfig
    strategy: StrategyConfig
    backtest: BacktestSettings
    market: MarketConfig
    costs: CostConfig
    metadata: dict[str, Any] = field(default_factory=dict)


def _require_section(raw: dict[str, Any], section: str) -> dict[str, Any]:
    value = raw.get(section)
    if not isinstance(value, dict):
        raise ValueError(f"missing or invalid [{section}] section in config")
    return value


def _require_value(section: dict[str, Any], section_name: str, key: str) -> Any:
    if key not in section or section[key] is None:
        raise ValueError(f"missing required key [{section_name}].{key}")
    return section[key]


def load_config(path: str | Path) -> BacktestConfig:
    config_path = Path(path)
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    data_raw = _require_section(raw, "data")
    strategy_raw = _require_section(raw, "strategy")
    backtest_raw = _require_section(raw, "backtest")
    market_raw = raw.get("market", {})
    costs_raw = raw.get("costs", {})

    data = DataConfig(
        source=str(_require_value(data_raw, "data", "source")),
        path=str(_require_value(data_raw, "data", "path")),
        format=str(data_raw.get("format", "csv")),
        adjustment=str(data_raw.get("adjustment", "none")),
    )
    strategy = StrategyConfig(
        name=str(_require_value(strategy_raw, "strategy", "name")),
        parameters=dict(strategy_raw.get("parameters", {})),
    )
    backtest = BacktestSettings(
        initial_cash=float(_require_value(backtest_raw, "backtest", "initial_cash")),
        holding_period_days=int(backtest_raw.get("holding_period_days", 1)),
        commission_rate=float(backtest_raw.get("commission_rate", 0.0003)),
        stamp_duty_rate=float(backtest_raw.get("stamp_duty_rate", 0.001)),
        minimum_commission=float(backtest_raw.get("minimum_commission", 5.0)),
        slippage_bps=float(backtest_raw.get("slippage_bps", 2.0)),
    )
    market = MarketConfig(
        index_symbol=str(market_raw.get("index_symbol", "000001.SH")),
        trigger_level=float(market_raw.get("trigger_level", 4000.0)),
        trigger_return_threshold=float(market_raw.get("trigger_return_threshold", 0.0)),
    )
    costs = CostConfig(
        commission_rate=float(costs_raw.get("commission_rate", backtest.commission_rate)),
        stamp_duty_rate=float(costs_raw.get("stamp_duty_rate", backtest.stamp_duty_rate)),
        minimum_commission=float(costs_raw.get("minimum_commission", backtest.minimum_commission)),
        slippage_bps=float(costs_raw.get("slippage_bps", backtest.slippage_bps)),
    )

    metadata = dict(raw.get("metadata", {}))
    metadata.setdefault("config_path", str(config_path))
    # Relative paths are defined against the directory containing the config.
    # Consumers may choose an explicit compatibility search path (the CLI does
    # this for the historical baseline fixture) before constructing a provider.
    raw_data_path = Path(data.path)
    if raw_data_path.is_absolute():
        resolved_data_path = raw_data_path.resolve()
    else:
        resolved_data_path = (config_path.parent / raw_data_path).resolve()
    metadata["data_path_resolved"] = str(resolved_data_path)

    return BacktestConfig(
        data=data,
        strategy=strategy,
        backtest=backtest,
        market=market,
        costs=costs,
        metadata=metadata,
    )
