"""Deterministic point-in-time strategy recommendations."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any
import math
import pandas as pd

from .domain import MarketState, Selection


@dataclass(frozen=True)
class Recommendation:
    as_of: date
    triggered: bool
    selected: Selection | None
    rankings: list[dict[str, Any]]
    filtered: list[dict[str, Any]]
    warnings: list[str]
    disclaimer: str = "Research output only; not investment advice or an instruction to trade."

    @property
    def selection(self) -> Selection | None:
        return self.selected

    @property
    def candidates(self) -> list[dict[str, Any]]:
        return self.rankings

    @property
    def filter_reasons(self) -> list[dict[str, Any]]:
        return self.filtered

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["as_of"] = self.as_of.isoformat()
        return result


def recommend(as_of: date, data: pd.DataFrame, strategy: Any) -> Recommendation:
    day = as_of.date() if isinstance(as_of, datetime) else (as_of if isinstance(as_of, date) else pd.Timestamp(as_of).date())
    frame = data.copy()
    warnings: list[str] = []
    required = {"date", "symbol", "close"}
    missing = required - set(frame.columns)
    if missing:
        return Recommendation(day, False, None, [], [], [f"missing required columns: {', '.join(sorted(missing))}"])
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame = frame.sort_values(["date", "symbol"], kind="stable").reset_index(drop=True)
    if frame["date"].isna().any(): warnings.append("data quality: invalid date values")
    if pd.to_numeric(frame["close"], errors="coerce").isna().any(): warnings.append("data quality: invalid close prices")
    history = frame[frame["date"] <= day]
    index_symbol = getattr(strategy, "index_symbol", "000001.SH")
    market = _market_state(history, day, index_symbol, getattr(strategy, "trigger_level", 4000.0), getattr(strategy, "trigger_return_threshold", 0.0))
    index_rows = history[history["symbol"] == index_symbol]
    if index_rows.empty:
        warnings.append(f"data quality: missing market index {index_symbol}")
    else:
        index_values = pd.to_numeric(index_rows["close"], errors="coerce")
        if index_values.isna().any() or (~index_values.map(math.isfinite)).any():
            warnings.append(f"data quality: invalid market index {index_symbol} close")
    if not market.triggered:
        warnings.append("market event not triggered")
    filtered: list[dict[str, Any]] = []
    symbols = list(getattr(strategy, "candidate_symbols", []) or [])
    if not symbols and getattr(strategy, "symbol", None):
        symbols = [strategy.symbol]
    for symbol in symbols:
        rows = history[history["symbol"] == symbol]
        latest = rows.iloc[-1] if not rows.empty else None
        reason = None
        if latest is None: reason = "no data as of date"
        elif latest["date"] != day: reason = "no bar on as_of date"
        elif any(bool(latest.get(c, False)) for c in ("is_suspended", "limit_up", "limit_down")): reason = "suspended or limit-up/down"
        if reason: filtered.append({"symbol": symbol, "reason": reason})
        elif not market.triggered:
            filtered.append({"symbol": symbol, "reason": "market event not triggered"})
    rankings: list[dict[str, Any]] = []
    if hasattr(strategy, "rank_candidates"):
        rankings = [dict(item) for item in strategy.rank_candidates(day, market, history)]
        explicit_filters = {item["symbol"]: item["reason"] for item in getattr(strategy, "last_filter_reasons", [])}
        ranked_symbols = {item.get("symbol") for item in rankings}
        for symbol in symbols:
            if symbol not in ranked_symbols and not any(item.get("symbol") == symbol for item in filtered):
                rows = history[history["symbol"] == symbol]
                if not rows.empty and rows.iloc[-1]["date"] == day:
                    filtered.append({"symbol": symbol, "reason": explicit_filters.get(symbol, "insufficient history or invalid features")})
    selected = strategy.select(day, market, history)
    if selected is not None and not any(item.get("symbol") == selected.symbol for item in rankings):
        rankings = [{"rank": 1, "symbol": selected.symbol, "score": selected.score, "features": selected.features, "reason": selected.reason}] + rankings
    rankings.sort(key=lambda item: (-float(item.get("score", 0)), str(item.get("symbol", ""))))
    for index, item in enumerate(rankings, 1): item["rank"] = index
    return Recommendation(day, market.triggered, selected, rankings, filtered, warnings)


def _market_state(frame: pd.DataFrame, day: date, index_symbol: str, trigger_level: float, threshold: float) -> MarketState:
    index = frame[(frame["symbol"] == index_symbol) & (frame["date"] <= day)].sort_values("date")
    if index.empty: return MarketState(day, 0.0, 0.0, False)
    try:
        latest = float(index.iloc[-1]["close"]); previous = float(index.iloc[-2]["close"]) if len(index) > 1 else latest
    except (TypeError, ValueError, OverflowError):
        return MarketState(day, 0.0, 0.0, False)
    if not pd.notna(latest) or not pd.notna(previous) or not math.isfinite(latest) or not math.isfinite(previous):
        return MarketState(day, 0.0, 0.0, False)
    ret = latest / previous - 1 if previous else 0.0
    return MarketState(day, latest, ret, latest >= trigger_level and ret < threshold)
