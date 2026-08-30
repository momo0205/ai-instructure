"""Deterministic, daily-bar backtesting and exchange-style order matching."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

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
        if initial_cash < 0 or holding_period_days < 1:
            raise ValueError("initial_cash must be non-negative and holding_period_days must be positive")
        if any(value < 0 for value in (commission_rate, stamp_duty_rate, minimum_commission, slippage_bps)):
            raise ValueError("cost and slippage parameters must be non-negative")
        self.initial_cash = float(initial_cash)
        self.holding_period_days = int(holding_period_days)
        self.commission_rate = float(commission_rate)
        self.stamp_duty_rate = float(stamp_duty_rate)
        self.minimum_commission = float(minimum_commission)
        self.slippage_bps = float(slippage_bps)
        self.index_symbol = index_symbol
        self.trigger_level = float(trigger_level)
        self.trigger_return_threshold = float(trigger_return_threshold)

    def run(self, market_data: pd.DataFrame, strategy: Any) -> BacktestResult:
        required = {"date", "symbol", "open", "close"}
        missing = required - set(market_data.columns)
        if missing:
            raise ValueError(f"market_data missing columns: {', '.join(sorted(missing))}")
        frame = market_data.copy()
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
        frame = frame.sort_values(["date", "symbol"], kind="stable").reset_index(drop=True)
        dates = list(frame["date"].drop_duplicates())
        cash = self.initial_cash
        position: dict[str, Any] | None = None
        pending_entry: tuple[date, str, date] | None = None
        pending_exit_date: date | None = None
        trades: list[Trade] = []
        warnings: list[str] = []
        equity: list[EquityPoint] = []
        peak = self.initial_cash

        for day_index, day in enumerate(dates):
            today = frame[frame["date"] == day]
            # Orders are matched at today's open before today's close signal.
            if pending_entry is not None and pending_entry[0] == day:
                _, symbol, signal_day = pending_entry
                row = self._row(today, symbol)
                pending_entry = None
                if row is None or self._blocked_entry(row):
                    warnings.append(f"entry not executed for {symbol} on {day} (suspended or limit-up/down)")
                else:
                    price = float(row["open"]) * (1 + self.slippage_bps / 10000)
                    quantity = self._quantity(cash, price)
                    if quantity > 0:
                        notional = quantity * price
                        commission = self._commission(notional)
                        cash -= notional + commission
                        position = {"symbol": symbol, "quantity": quantity, "entry_price": price,
                                    "signal_date": signal_day, "entry_date": day,
                                    "entry_fees": commission, "last_close": float(row["close"]),
                                    "missing_price_warned": False}
                        exit_idx = day_index + self.holding_period_days
                        pending_exit_date = dates[exit_idx] if exit_idx < len(dates) else None
                    else:
                        warnings.append(f"entry not executed for {symbol} on {day} (insufficient cash)")

            if position is not None and pending_exit_date is not None and day >= pending_exit_date:
                row = self._row(today, position["symbol"])
                if row is not None and not self._blocked_exit(row):
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
                if row is not None:
                    position["last_close"] = float(row["close"])
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
                market = self._market_state(frame, day)
                selection = strategy.select(day, market, universe)
                if selection is not None:
                    pending_entry = (dates[day_index + 1], selection.symbol, day)
            elif position is None and pending_entry is None and day_index == len(dates) - 1:
                # A final-day signal cannot be executed within the supplied data.
                market = self._market_state(frame, day)
                selection = strategy.select(day, market, frame[frame["date"] <= day].copy())
                if selection is not None:
                    warnings.append(f"incomplete trade: signal on {day} has no next trading day")

        if position is not None:
            warnings.append(f"incomplete trade: open position {position['symbol']} has no executable exit")
        return BacktestResult(trades, equity, warnings)

    def _market_state(self, frame: pd.DataFrame, day: date) -> MarketState:
        index = frame[(frame["symbol"] == self.index_symbol) & (frame["date"] <= day)].sort_values("date")
        if index.empty:
            return MarketState(day, 0.0, 0.0, True)
        latest = index.iloc[-1]
        previous = index.iloc[-2] if len(index) > 1 else latest
        previous_close = float(previous["close"])
        ret = float(latest["close"]) / previous_close - 1 if previous_close else 0.0
        return MarketState(day, float(latest["close"]), ret,
                           float(latest["close"]) >= self.trigger_level and ret < self.trigger_return_threshold)

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

    def _commission(self, notional: float) -> float:
        return max(self.minimum_commission, notional * self.commission_rate) if notional else 0.0

    def _quantity(self, cash: float, price: float) -> float:
        if price <= 0 or cash <= self.minimum_commission:
            return 0.0
        return max(0.0, (cash - self.minimum_commission) / (price * (1 + self.commission_rate)))
