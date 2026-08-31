"""Deterministic, daily-bar backtesting and exchange-style order matching."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Any

import pandas as pd

from .data import BOOL_COLUMNS, REQUIRED_MARKET_COLUMNS, validate_market_frame
from .domain import EquityPoint, MarketState, Trade


@dataclass(frozen=True, slots=True)
class BacktestResult:
    trades: list[Trade]
    equity: list[EquityPoint]
    warnings: list[str]


class BacktestEngine:
    def __init__(self, initial_cash: float, holding_period_days: int = 1,
                 commission_rate: float = 0.0003, stamp_duty_rate: float = 0.001,
                 minimum_commission: float = 5.0, slippage_bps: float = 2.0,
                 index_symbol: str = "000001.SH", trigger_level: float = 4000.0,
                 trigger_return_threshold: float = 0.0):
        try:
            cash_value = float(initial_cash)
            period_value = float(holding_period_days)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("initial_cash must be non-negative and holding_period_days must be positive") from None
        if (not math.isfinite(cash_value) or cash_value < 0 or not math.isfinite(period_value)
                or period_value < 1 or not period_value.is_integer()):
            raise ValueError("initial_cash must be non-negative and holding_period_days must be positive")
        try:
            parameters = tuple(float(value) for value in (commission_rate, stamp_duty_rate, minimum_commission, slippage_bps))
        except (TypeError, ValueError, OverflowError):
            raise ValueError("cost and slippage parameters must be finite") from None
        if any(not math.isfinite(value) for value in parameters):
            raise ValueError("cost and slippage parameters must be finite")
        if any(value < 0 for value in parameters):
            raise ValueError("cost and slippage parameters must be non-negative")
        self.initial_cash = cash_value
        self.holding_period_days = int(period_value)
        self.commission_rate, self.stamp_duty_rate, self.minimum_commission, self.slippage_bps = parameters
        self.index_symbol = index_symbol
        try:
            trigger_values = (float(trigger_level), float(trigger_return_threshold))
        except (TypeError, ValueError, OverflowError):
            raise ValueError("market trigger parameters must be finite") from None
        if any(not math.isfinite(value) for value in trigger_values):
            raise ValueError("market trigger parameters must be finite")
        self.trigger_level, self.trigger_return_threshold = trigger_values

    def run(self, market_data: pd.DataFrame, strategy: Any) -> BacktestResult:
        # Validate before sorting or simulating so callers cannot bypass the
        # daily/duplicate/positive-price data contract.
        frame = self._validation_frame(market_data)
        required = set(REQUIRED_MARKET_COLUMNS)
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"market_data missing required columns: {', '.join(sorted(missing))}")
        validate_market_frame(frame, allow_nonfinite_price_columns={"open", "close"})
        frame = frame.copy()
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
        frame = frame.sort_values(["date", "symbol"], kind="stable").reset_index(drop=True)
        dates = list(frame["date"].drop_duplicates())
        cash = self.initial_cash
        position: dict[str, Any] | None = None
        pending_entry: tuple[date, str, date] | None = None
        pending_exit_date: date | None = None
        trades: list[Trade] = []
        warnings: list[str] = []
        warning_set: set[str] = set()
        equity: list[EquityPoint] = []
        peak = self.initial_cash

        for day_index, day in enumerate(dates):
            today = frame[frame["date"] == day]
            market, market_warning = self._market_state_with_warning(frame, day)
            if market_warning and market_warning not in warning_set:
                warnings.append(market_warning)
                warning_set.add(market_warning)
            # Orders are matched at today's open before today's close signal.
            if pending_entry is not None and pending_entry[0] == day:
                _, symbol, signal_day = pending_entry
                row = self._row(today, symbol)
                pending_entry = None
                # The close is not known at next-open execution; only the open
                # and tradability flags can gate entry (future-data cutoff).
                if row is None or self._blocked_entry(row) or not self._valid_prices(row, "open"):
                    warnings.append(f"entry not executed for {symbol} on {day} (suspended or limit-up/down)")
                else:
                    price = float(row["open"]) * (1 + self.slippage_bps / 10000)
                    quantity = self._quantity(cash, price)
                    if quantity > 0:
                        notional = quantity * price
                        commission = self._commission(notional)
                        cash -= notional + commission
                        initial_close = None
                        if self._valid_prices(row, "close"):
                            initial_close = float(row["close"])
                        position = {"symbol": symbol, "quantity": quantity, "entry_price": price,
                                    "signal_date": signal_day, "entry_date": day,
                                    "entry_fees": commission, "last_close": initial_close,
                                    "missing_price_warned": False}
                        exit_idx = day_index + self.holding_period_days
                        pending_exit_date = dates[exit_idx] if exit_idx < len(dates) else None
                    else:
                        warnings.append(f"entry not executed for {symbol} on {day} (insufficient cash)")

            if position is not None and pending_exit_date is not None and day >= pending_exit_date:
                row = self._row(today, position["symbol"])
                if row is not None and not self._blocked_exit(row) and self._valid_prices(row, "open"):
                    price = float(row["open"]) * (1 - self.slippage_bps / 10000)
                    notional = position["quantity"] * price
                    commission = self._commission(notional)
                    tax = notional * self.stamp_duty_rate
                    cash += notional - commission - tax
                    fees = position["entry_fees"] + commission + tax
                    gross = (price - position["entry_price"]) * position["quantity"]
                    trades.append(Trade(position["signal_date"], position["entry_date"], day,
                                        position["symbol"], position["quantity"], position["entry_price"],
                                        price, fees, gross - fees, "holding period"))
                    position = None
                    pending_exit_date = None

            mark = 0.0
            if position is not None:
                row = self._row(today, position["symbol"])
                if row is not None and self._valid_prices(row, "close"):
                    position["last_close"] = float(row["close"])
                elif row is not None and not position["missing_price_warned"]:
                    warnings.append(f"cannot mark open position {position['symbol']}: non-finite close")
                    position["missing_price_warned"] = True
                if position["last_close"] is not None:
                    mark = position["quantity"] * position["last_close"]
                elif not position["missing_price_warned"]:
                    warnings.append(f"cannot mark open position {position['symbol']}: no known close")
                    position["missing_price_warned"] = True
            total = cash + mark
            peak = max(peak, total)
            equity.append(EquityPoint(day, cash, mark, total, (total / peak - 1) if peak else 0.0))

            # Signal is evaluated only after this day's data is complete.
            if position is None and pending_entry is None and day_index + 1 < len(dates):
                universe = frame[frame["date"] <= day].copy()
                selection = strategy.select(day, market, universe)
                if selection is not None:
                    pending_entry = (dates[day_index + 1], selection.symbol, day)
            elif position is None and pending_entry is None and day_index == len(dates) - 1:
                # A final-day signal cannot be executed within the supplied data.
                selection = strategy.select(day, market, frame[frame["date"] <= day].copy())
                if selection is not None:
                    warnings.append(f"incomplete trade: signal on {day} has no next trading day")

        if position is not None:
            warnings.append(f"incomplete trade: open position {position['symbol']} has no executable exit")
        return BacktestResult(trades, equity, warnings)

    def _market_state(self, frame: pd.DataFrame, day: date) -> MarketState:
        index = frame[(frame["symbol"] == self.index_symbol) & (frame["date"] <= day)].sort_values("date")
        if index.empty:
            return MarketState(day, 0.0, 0.0, False)
        try:
            history_closes = [float(value) for value in index["close"]]
            if not all(math.isfinite(value) and value > 0 for value in history_closes):
                return MarketState(day, 0.0, 0.0, False)
        except (TypeError, ValueError, OverflowError):
            return MarketState(day, 0.0, 0.0, False)
        latest = index.iloc[-1]
        previous = index.iloc[-2] if len(index) > 1 else latest
        try:
            latest_close = float(latest["close"])
            previous_close = float(previous["close"])
            if not (math.isfinite(latest_close) and math.isfinite(previous_close)):
                return MarketState(day, 0.0, 0.0, False)
            if latest_close <= 0 or previous_close <= 0:
                return MarketState(day, 0.0, 0.0, False)
            ret = latest_close / previous_close - 1
            if not math.isfinite(ret):
                return MarketState(day, 0.0, 0.0, False)
        except (TypeError, ValueError, OverflowError, ZeroDivisionError):
            return MarketState(day, 0.0, 0.0, False)
        return MarketState(day, latest_close, ret,
                           latest_close >= self.trigger_level and ret < self.trigger_return_threshold)

    def _market_state_with_warning(self, frame: pd.DataFrame, day: date) -> tuple[MarketState, str | None]:
        """Return the fail-closed trigger and a user-visible data-quality reason."""
        history = frame[(frame["symbol"] == self.index_symbol) & (frame["date"] <= day)].sort_values("date")
        if history.empty:
            return MarketState(day, 0.0, 0.0, False), f"data quality: missing market index {self.index_symbol}"
        values = history["close"].tolist()
        try:
            valid = all(math.isfinite(float(value)) and float(value) > 0 for value in values)
        except (TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            return MarketState(day, 0.0, 0.0, False), f"data quality: invalid market index {self.index_symbol} close"
        return self._market_state(frame, day), None

    @staticmethod
    def _validation_frame(market_data: pd.DataFrame) -> pd.DataFrame:
        """Copy input and retain only narrow compatibility for omitted flags."""
        if not isinstance(market_data, pd.DataFrame):
            raise TypeError("market_data must be a pandas DataFrame")
        frame = market_data.copy()
        # A legacy helper built high/low directly from a missing open. Restore
        # those mechanically-derived fields from the known close, then apply
        # the full validator so independently malformed high/low values fail.
        open_values = pd.to_numeric(frame["open"], errors="coerce") if "open" in frame else None
        close_values = pd.to_numeric(frame["close"], errors="coerce") if "close" in frame else None
        if open_values is not None and close_values is not None:
            repair = (~pd.Series(open_values).map(math.isfinite)
                      & pd.Series(close_values).map(math.isfinite))
            for column in ("high", "low"):
                if column in frame:
                    bad = ~pd.to_numeric(frame[column], errors="coerce").map(math.isfinite)
                    frame.loc[repair & bad, column] = close_values[repair & bad]
        missing = set(REQUIRED_MARKET_COLUMNS) - set(frame.columns)
        # A few legacy report fixtures omitted every tradability flag; keep
        # that narrow compatibility case while requiring all market values.
        missing_flags = missing & set(BOOL_COLUMNS)
        # Partial flags leave tradability unknown, so fail closed.
        if missing_flags and missing_flags != set(BOOL_COLUMNS):
            raise ValueError(f"market_data missing tradability columns: {', '.join(sorted(missing_flags))}")
        if missing and missing <= set(BOOL_COLUMNS):
            for column in BOOL_COLUMNS:
                if column not in frame:
                    frame[column] = False
            missing = set(REQUIRED_MARKET_COLUMNS) - set(frame.columns)
        return frame

    @staticmethod
    def _row(day_frame: pd.DataFrame, symbol: str):
        rows = day_frame[day_frame["symbol"] == symbol]
        return None if rows.empty else rows.iloc[0]

    @staticmethod
    def _blocked_entry(row) -> bool:
        return any(bool(row.get(column, False)) for column in ("is_suspended", "limit_up", "limit_down"))

    @staticmethod
    def _blocked_exit(row) -> bool:
        return bool(row.get("is_suspended", False) or row.get("limit_down", False))

    @staticmethod
    def _valid_prices(row, *columns: str) -> bool:
        try:
            return all(math.isfinite(float(row[column])) for column in columns)
        except (TypeError, ValueError):
            return False

    def _commission(self, notional: float) -> float:
        # Apply exchange-style percentage commission with the configured floor
        # so every reported trade includes explicit, reproducible costs.
        return max(self.minimum_commission, notional * self.commission_rate) if notional else 0.0

    def _quantity(self, cash: float, price: float) -> float:
        if price <= 0 or cash <= self.minimum_commission:
            return 0.0
        return max(0.0, (cash - self.minimum_commission) / (price * (1 + self.commission_rate)))
