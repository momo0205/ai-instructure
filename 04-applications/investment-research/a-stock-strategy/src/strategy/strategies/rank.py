from datetime import date
import numpy as np
import pandas as pd
from ..domain import MarketState, Selection


class CrossSectionalRankStrategy:
    def __init__(self, candidate_symbols=None, momentum_window: int = 20, reversal_window: int = 3,
                 volatility_window: int = 20, volume_window: int = 5, weights=None, min_volume: float = 0.0):
        self.candidate_symbols = list(candidate_symbols or [])
        try:
            windows = tuple(self._positive_int(value) for value in
                            (momentum_window, reversal_window, volatility_window, volume_window))
        except (TypeError, ValueError, OverflowError):
            raise ValueError("ranking windows must be positive")
        self.momentum_window, self.reversal_window, self.volatility_window, self.volume_window = windows
        base_weights = {"momentum": 1.0, "reversal": 0.0, "volatility": 0.0, "volume": 0.0}
        supplied_weights = dict(weights or {})
        unknown_weights = set(supplied_weights) - set(base_weights)
        if unknown_weights:
            raise ValueError(f"unknown ranking weights: {', '.join(sorted(map(str, unknown_weights)))}")
        self.weights = base_weights | supplied_weights
        try:
            self.min_volume = float(min_volume)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("min_volume must be finite and non-negative") from None
        if not np.isfinite(self.min_volume) or self.min_volume < 0:
            raise ValueError("min_volume must be finite and non-negative")
        try:
            self.weights = {key: float(value) for key, value in self.weights.items()}
        except (TypeError, ValueError, OverflowError):
            raise ValueError("ranking weights must be finite") from None
        if any(not np.isfinite(value) for value in self.weights.values()):
            raise ValueError("ranking weights must be finite")
        self.last_filter_reasons: list[dict[str, str]] = []

    @staticmethod
    def _positive_int(value) -> int:
        numeric = float(value)
        if not np.isfinite(numeric) or numeric < 1 or not numeric.is_integer():
            raise ValueError
        return int(numeric)

    @staticmethod
    def _z(values):
        std = values.std(ddof=0)
        return (values - values.mean()) / std if std and np.isfinite(std) else values * 0.0

    def select(self, as_of: date, market: MarketState, universe: pd.DataFrame) -> Selection | None:
        if not market.triggered or universe.empty or not self.candidate_symbols:
            return None
        ranked = self.rank_candidates(as_of, market, universe)
        if not ranked:
            return None
        top = ranked[0]
        features = dict(top.get("features", {}))
        return Selection(str(top["symbol"]), float(top["score"]), features, "highest standardized cross-sectional score")

    def rank_candidates(self, as_of: date, market: MarketState, universe: pd.DataFrame) -> list[dict]:
        self.last_filter_reasons = []
        if not market.triggered or universe.empty or not self.candidate_symbols:
            return []
        frame = universe.copy()
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame[(frame["date"].dt.date <= as_of) & frame["symbol"].isin(self.candidate_symbols)].sort_values(["symbol", "date"])
        records = []
        for symbol, hist in frame.groupby("symbol", sort=True):
            latest = hist.iloc[-1]
            # Filters run before feature math; rejected symbols are retained as
            # diagnostics by recommendation, never as NaN/inf-ranked rows.
            if latest["date"].date() != as_of:
                self.last_filter_reasons.append({"symbol": str(symbol), "reason": "no bar on as_of date"})
                continue
            if any(bool(latest.get(c, False)) for c in ("is_suspended", "limit_up", "limit_down")):
                self.last_filter_reasons.append({"symbol": str(symbol), "reason": "suspended or limit-up/down"})
                continue
            try:
                latest_volume = float(latest.get("volume", 0) or 0)
            except (TypeError, ValueError, OverflowError):
                latest_volume = float("nan")
            if not np.isfinite(latest_volume) or latest_volume < self.min_volume:
                self.last_filter_reasons.append({"symbol": str(symbol), "reason": "invalid or below minimum latest volume"})
                continue
            close = pd.to_numeric(hist["close"], errors="coerce")
            volume = pd.to_numeric(hist.get("volume", pd.Series(index=hist.index, dtype=float)), errors="coerce")
            required = max(self.momentum_window, self.reversal_window, self.volatility_window, self.volume_window) + 1
            if len(close) < required:
                self.last_filter_reasons.append({"symbol": str(symbol), "reason": "insufficient history"})
                continue
            if close.isna().any() or not np.isfinite(close.to_numpy(dtype=float)).all():
                self.last_filter_reasons.append({"symbol": str(symbol), "reason": "invalid close history"})
                continue
            if volume.isna().any() or not np.isfinite(volume.to_numpy(dtype=float)).all():
                self.last_filter_reasons.append({"symbol": str(symbol), "reason": "invalid volume history"})
                continue
            close = close.reset_index(drop=True)
            ret = close.pct_change().dropna()
            momentum = close.iloc[-1] / close.iloc[-1-self.momentum_window] - 1
            reversal = -(close.iloc[-1] / close.iloc[-1-self.reversal_window] - 1)
            volatility = ret.tail(self.volatility_window).std(ddof=0) if len(ret) > 1 else 0.0
            volume = volume.reset_index(drop=True)
            prior_volume = float(volume.iloc[-1-self.volume_window])
            if not np.isfinite(prior_volume) or prior_volume <= 0:
                self.last_filter_reasons.append({"symbol": str(symbol), "reason": "invalid prior volume for volume-change feature"})
                continue
            volume_change = float(volume.iloc[-1]) / prior_volume - 1
            values = (momentum, reversal, volatility, volume_change)
            if not all(np.isfinite(value) for value in values):
                self.last_filter_reasons.append({"symbol": str(symbol), "reason": "non-finite ranking feature"})
                continue
            records.append({"symbol": symbol, "momentum": momentum, "reversal": reversal, "volatility": volatility, "volume": volume_change})
        if not records:
            return []
        scores = pd.DataFrame(records)
        if scores.empty:
            return []
        score = sum(self.weights[k] * self._z(scores[k]) for k in self.weights)
        if not np.isfinite(score.to_numpy(dtype=float)).all():
            return []
        ranked = []
        for idx in score.sort_values(ascending=False, kind="stable").index:
            row = scores.loc[idx]
            features = {k: float(row[k]) for k in self.weights} | {"as_of": as_of.isoformat()}
            ranked.append({"symbol": str(row["symbol"]), "score": float(score.loc[idx]), "features": features,
                           "reason": "highest standardized cross-sectional score"})
        return ranked
