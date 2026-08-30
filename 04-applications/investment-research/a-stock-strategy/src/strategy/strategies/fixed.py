from datetime import date
import pandas as pd
from ..domain import MarketState, Selection


class FixedAssetStrategy:
    def __init__(self, symbol: str = "588000.SH"):
        self.symbol = symbol

    def select(self, as_of: date, market: MarketState, universe: pd.DataFrame) -> Selection | None:
        if not market.triggered or universe.empty or "symbol" not in universe or "date" not in universe:
            return None
        rows = universe[(universe["symbol"] == self.symbol) & (pd.to_datetime(universe["date"]).dt.date == as_of)]
        if rows.empty:
            return None
        row = rows.sort_values("date").iloc[-1]
        if any(bool(row.get(c, False)) for c in ("is_suspended", "limit_up", "limit_down")):
            return None
        return Selection(self.symbol, 0.0, {"as_of": as_of.isoformat()}, "market trigger: fixed asset")
