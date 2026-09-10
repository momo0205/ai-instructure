"""Deterministic point-in-time strategy recommendations."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any
import math
from numbers import Real
import pandas as pd

from strategy.domain import MarketState, Selection
from strategy.backtesting.signals import market_state


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
        return _json_safe(result)


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
    history = frame[frame["date"] <= day]
    # Quality diagnostics are point-in-time: future rows must not influence an
    # as-of recommendation or make a historical report appear unsafe.
    if history["date"].isna().any(): warnings.append("data quality: invalid date values")
    close_values = pd.to_numeric(history["close"], errors="coerce")
    if close_values.isna().any() or not _finite_values(close_values):
        warnings.append("data quality: invalid close prices")
    index_symbol = getattr(strategy, "index_symbol", "000001.SH")
    try:
        trigger_level = float(getattr(strategy, "trigger_level", 4000.0))
        threshold = float(getattr(strategy, "trigger_return_threshold", 0.0))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("market trigger parameters must be finite") from None
    if not math.isfinite(trigger_level) or not math.isfinite(threshold):
        raise ValueError("market trigger parameters must be finite")
    market, market_warning = market_state(history, day, index_symbol, trigger_level, threshold,
                                         getattr(strategy, "min_declining_count", None))
    if market_warning:
        warnings.append(market_warning)
    index_rows = history[history["symbol"] == index_symbol]
    if index_rows.empty:
        warnings.append(f"data quality: missing market index {index_symbol}")
    else:
        index_values = pd.to_numeric(index_rows["close"], errors="coerce")
        if index_values.isna().any() or not _finite_values(index_values):
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


def _finite_values(values: pd.Series) -> bool:
    try:
        return bool(values.notna().all() and values.map(float).map(math.isfinite).all())
    except (TypeError, ValueError, OverflowError):
        return False


def _json_safe(value: Any) -> Any:
    if isinstance(value, Real) and not isinstance(value, bool):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value
