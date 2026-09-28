from __future__ import annotations

from datetime import date
from typing import Protocol
import pandas as pd

from strategy.domain import MarketState, Selection


class Strategy(Protocol):
    def select(self, as_of: date, market: MarketState, universe: pd.DataFrame) -> Selection | None: ...
