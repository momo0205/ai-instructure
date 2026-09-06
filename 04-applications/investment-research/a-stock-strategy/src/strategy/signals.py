"""One point-in-time market trigger shared by simulation and recommendation."""
from datetime import date
import math
import pandas as pd
from .domain import MarketState


class MarketTrigger:
    def __init__(self, trigger_level=4000.0, trigger_return_threshold=0.0, as_of=None,
                 min_declining_count=None):
        self.trigger_level = float(trigger_level)
        self.trigger_return_threshold = float(trigger_return_threshold)
        if not all(math.isfinite(v) for v in (self.trigger_level, self.trigger_return_threshold)):
            raise ValueError("market trigger parameters must be finite")
        if min_declining_count is not None:
            value = float(min_declining_count)
            if not math.isfinite(value) or value < 0 or not value.is_integer():
                raise ValueError("min_declining_count must be a non-negative integer")
            min_declining_count = int(value)
        self.min_declining_count = min_declining_count
        self.as_of = as_of

    def evaluate(self, index_level, index_return_1d, as_of=None, *, declining_count=None):
        when = as_of or self.as_of
        if when is None:
            raise ValueError("as_of is required for deterministic market evaluation")
        level, ret = float(index_level), float(index_return_1d)
        count = None
        try:
            value = float(declining_count)
            if math.isfinite(value) and value >= 0 and value.is_integer():
                count = int(value)
        except (TypeError, ValueError, OverflowError):
            pass
        valid = math.isfinite(level) and level > 0 and math.isfinite(ret)
        if self.min_declining_count is not None:
            triggered = (valid and count is not None and count >= self.min_declining_count
                         and ret <= self.trigger_return_threshold + 1e-12)
        else:
            # Explicit legacy API compatibility; MVP config uses breadth.
            triggered = valid and level >= self.trigger_level and ret < self.trigger_return_threshold
        return MarketState(when, level, ret, bool(triggered), count)


def market_state(frame, day: date, index_symbol="000001.SH", trigger_level=4000.0,
                 threshold=0.0, min_declining_count=None):
    trigger = MarketTrigger(trigger_level, threshold, min_declining_count=min_declining_count)
    dates = pd.to_datetime(frame["date"]).dt.date
    index = frame[(frame["symbol"] == index_symbol) & (dates <= day)].sort_values("date")
    empty = MarketState(day, 0.0, 0.0, False)
    if index.empty or pd.Timestamp(index.iloc[-1]["date"]).date() != day:
        return empty, f"data quality: missing market index {index_symbol} on {day}"
    values = pd.to_numeric(index["close"], errors="coerce")
    if not values.map(lambda v: pd.notna(v) and math.isfinite(v) and v > 0).all():
        return empty, f"data quality: invalid market index {index_symbol} close"
    latest = index.iloc[-1]
    supplied_return = latest.get("index_return_1d")
    if supplied_return is not None and pd.notna(supplied_return):
        ret = float(supplied_return)
        if not math.isfinite(ret):
            return empty, f"data quality: invalid market index return on {day}"
    else:
        earlier_days = sorted(set(dates[dates < day]))
        if len(index) < 2 or (earlier_days and pd.Timestamp(index.iloc[-2]["date"]).date() != earlier_days[-1]):
            return empty, f"data quality: missing previous market index close on {day}"
        ret = float(values.iloc[-1]) / float(values.iloc[-2]) - 1
    state = trigger.evaluate(values.iloc[-1], ret, day, declining_count=latest.get("declining_count"))
    if min_declining_count is not None and state.declining_count is None:
        return state, f"data quality: missing or invalid market breadth on {day}"
    return state, None
