from datetime import date

from .domain import MarketState


class MarketTrigger:
    def __init__(self, trigger_level: float = 4000.0, trigger_return_threshold: float = 0.0, as_of: date | None = None):
        self.trigger_level = float(trigger_level)
        self.trigger_return_threshold = float(trigger_return_threshold)
        self.as_of = as_of

    def evaluate(self, index_level: float, index_return_1d: float, as_of: date | None = None) -> MarketState:
        when = as_of or self.as_of
        if when is None:
            raise ValueError("as_of is required for deterministic market evaluation")
        return MarketState(when, float(index_level), float(index_return_1d),
                           float(index_level) >= self.trigger_level and float(index_return_1d) < self.trigger_return_threshold)
