from datetime import date
import numpy as np
import pandas as pd
from ..domain import MarketState, Selection


class CrossSectionalRankStrategy:
    def __init__(self, candidate_symbols=None, momentum_window: int = 20, reversal_window: int = 3,
                 volatility_window: int = 20, volume_window: int = 5, weights=None, min_volume: float = 0.0):
        self.candidate_symbols = list(candidate_symbols or [])
        self.momentum_window, self.reversal_window = int(momentum_window), int(reversal_window)
        self.volatility_window, self.volume_window = int(volatility_window), int(volume_window)
        self.weights = {"momentum": 1.0, "reversal": 0.0, "volatility": 0.0, "volume": 0.0} | dict(weights or {})
        self.min_volume = float(min_volume)

    @staticmethod
    def _z(values):
        std = values.std(ddof=0)
        return (values - values.mean()) / std if std and np.isfinite(std) else values * 0.0

    def select(self, as_of: date, market: MarketState, universe: pd.DataFrame) -> Selection | None:
        if not market.triggered or universe.empty or not self.candidate_symbols:
            return None
        frame = universe.copy()
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame[(frame["date"].dt.date <= as_of) & frame["symbol"].isin(self.candidate_symbols)].sort_values(["symbol", "date"])
        records = []
        for symbol, hist in frame.groupby("symbol", sort=True):
            latest = hist.iloc[-1]
            if latest["date"].date() != as_of:
                continue
            if any(bool(latest.get(c, False)) for c in ("is_suspended", "limit_up", "limit_down")) or float(latest.get("volume", 0) or 0) < self.min_volume:
                continue
            close = pd.to_numeric(hist["close"], errors="coerce")
            volume = pd.to_numeric(hist.get("volume", pd.Series(index=hist.index, dtype=float)), errors="coerce")
            required = max(self.momentum_window, self.reversal_window, self.volatility_window, self.volume_window) + 1
            if len(close) < required or close.isna().any() or volume.isna().any():
                continue
            close = close.reset_index(drop=True)
            ret = close.pct_change().dropna()
            momentum = close.iloc[-1] / close.iloc[-1-self.momentum_window] - 1
            reversal = -(close.iloc[-1] / close.iloc[-1-self.reversal_window] - 1)
            volatility = ret.tail(self.volatility_window).std(ddof=0) if len(ret) > 1 else 0.0
            volume = volume.reset_index(drop=True)
            volume_change = volume.iloc[-1] / volume.iloc[-1-self.volume_window] - 1
            records.append({"symbol": symbol, "momentum": momentum, "reversal": reversal, "volatility": volatility, "volume": volume_change})
        if not records:
            return None
        scores = pd.DataFrame(records)
        if scores.empty:
            return None
        score = sum(self.weights[k] * self._z(scores[k]) for k in self.weights)
        idx = score.idxmax(); row = scores.loc[idx]
        features = {k: float(row[k]) for k in self.weights} | {"as_of": as_of.isoformat()}
        return Selection(str(row["symbol"]), float(score.loc[idx]), features, "highest standardized cross-sectional score")
