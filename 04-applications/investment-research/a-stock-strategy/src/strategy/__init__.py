from strategy.application.configuration import (
    BacktestConfig,
    BacktestSettings,
    CostConfig,
    DataConfig,
    MarketConfig,
    StrategyConfig,
    load_config,
)
from strategy.market_data.csv import CsvMarketDataProvider, REQUIRED_MARKET_COLUMNS, validate_market_frame
from strategy.market_data.sources import (
    AStockDataProvider,
    BaiduKlineFetcher,
    MootdxBarFetcher,
    MootdxIndexFetcher,
    normalize_daily_bars,
)
from strategy.domain import EquityPoint, MarketState, Selection, Trade
from strategy.backtesting.evaluation import Metrics, evaluate

__all__ = [
    "BacktestConfig",
    "BacktestSettings",
    "AStockDataProvider",
    "BaiduKlineFetcher",
    "MootdxBarFetcher",
    "MootdxIndexFetcher",
    "CostConfig",
    "CsvMarketDataProvider",
    "DataConfig",
    "EquityPoint",
    "MarketConfig",
    "MarketState",
    "Metrics",
    "REQUIRED_MARKET_COLUMNS",
    "Selection",
    "StrategyConfig",
    "Trade",
    "load_config",
    "normalize_daily_bars",
    "evaluate",
    "validate_market_frame",
]

# 历史导入集中映射到规范模块，同一对象保证旧插件与monkeypatch语义不变。
from ._compat import install as _install_legacy_imports
_install_legacy_imports()
del _install_legacy_imports
