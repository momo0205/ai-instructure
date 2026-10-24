"""纯指标：按研究交易日对齐，缺失数据不跳过，不接触账户或撮合。"""
from dataclasses import dataclass
import math

from .catalog import indicator_catalog, normalize_instances
from .series import calculate_series

SMA_VERSION = 'sma-v1'
SMA_METADATA = {'id': 'sma', 'version': SMA_VERSION, 'formula': 'sum(close[-N:]) / N',
                'required_fields': ['close'], 'window': '连续 N 个研究交易日，含当日'}


@dataclass(frozen=True)
class IndicatorValue:
    value: float | None
    available: int
    window: int
    reason: str


def simple_moving_average(history, symbol, day, window):
    """只读取截至 day 的窗口；其他证券只定义日历，不贡献价格。"""
    past = history[history['date'] <= day]
    dates = sorted(past['date'].unique())[-window:]
    prices = past[past['symbol'] == symbol].set_index('date')['close'].reindex(dates)
    valid = prices.map(lambda v: isinstance(v, (int, float)) and math.isfinite(v) and v > 0)
    available = int(valid.sum())
    ready = len(dates) == window and available == window
    return IndicatorValue(float(prices.mean()) if ready else None, available, window,
                          '' if ready else 'indicator_unavailable')
