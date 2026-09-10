"""Deterministic, daily-bar backtesting and exchange-style order matching."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
import math
from typing import Any

import pandas as pd

from strategy.market_data.csv import BOOL_COLUMNS, REQUIRED_MARKET_COLUMNS, validate_market_frame
from strategy.domain import EquityPoint, MarketState, Trade
from strategy.backtesting.fees import FeeRules
from strategy.backtesting.signals import market_state, MarketTrigger
from strategy.backtesting.tradability import DailyBarStatusProvider, StatusProvider, execution_block


@dataclass(frozen=True, slots=True)
class BacktestResult:
    trades: list[Trade]
    equity: list[EquityPoint]
    warnings: list[str]
    events: list[dict] = field(default_factory=list)
    execution_events: list[dict] = field(default_factory=list)


class BacktestEngine:
    def __init__(self, initial_cash: float, holding_period_days: int = 1,
                 commission_rate: float = 0.0003, stamp_duty_rate: float = 0.001,
                 minimum_commission: float = 5.0, slippage_bps: float = 2.0,
                 index_symbol: str = "000001.SH", trigger_level: float = 4000.0,
                 trigger_return_threshold: float = 0.0, min_declining_count=None, lot_size: int = 0,
                 instrument_types: dict[str, str] | None = None,
                 status_provider: StatusProvider | None = None):
        self.status_provider = status_provider or DailyBarStatusProvider()
        if instrument_types is not None and any(kind not in {"stock", "etf"} for kind in instrument_types.values()):
            raise ValueError("instrument_types values must be stock or etf")
        self.instrument_types = None if instrument_types is None else dict(instrument_types)
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
        self.fee_rules = FeeRules(self.commission_rate, self.minimum_commission, self.stamp_duty_rate)
        self.index_symbol = index_symbol
        self.min_declining_count = MarketTrigger(min_declining_count=min_declining_count).min_declining_count
        if not math.isfinite(float(lot_size)) or float(lot_size) < 0 or not float(lot_size).is_integer():
            raise ValueError("lot_size must be a non-negative integer")
        self.lot_size = int(lot_size)
        try:
            trigger_values = (float(trigger_level), float(trigger_return_threshold))
        except (TypeError, ValueError, OverflowError):
            raise ValueError("market trigger parameters must be finite") from None
        if any(not math.isfinite(value) for value in trigger_values):
            raise ValueError("market trigger parameters must be finite")
        self.trigger_level, self.trigger_return_threshold = trigger_values

    def run(self, market_data: pd.DataFrame, strategy: Any, *, start: date | None = None, end: date | None = None) -> BacktestResult:
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
        # 起始日前的数据保留给指标预热，但不产生交易、信号或净值。
        dates = [day for day in frame["date"].drop_duplicates()
                 if (start is None or day >= start) and (end is None or day <= end)]
        cash = self.initial_cash
        position: dict[str, Any] | None = None
        pending_entry: tuple[date, str, date] | None = None
        pending_exit_date: date | None = None
        trades: list[Trade] = []
        events = []
        execution_events = []
        warnings: list[str] = []
        warning_set: set[str] = set()
        equity: list[EquityPoint] = []
        peak = self.initial_cash

        for day_index, day in enumerate(dates):
            today = frame[frame["date"] == day]
            market, market_warning = self._market_state_with_warning(frame, day)
            events.append(asdict(market) | {"warning": market_warning})
            if market_warning and market_warning not in warning_set:
                warnings.append(market_warning)
                warning_set.add(market_warning)
            # Orders are matched at today's open before today's close signal.
            if pending_entry is not None and pending_entry[0] == day:
                _, symbol, signal_day = pending_entry
                kind = self._instrument_type(symbol, day)
                row = self._row(today, symbol)
                pending_entry = None
                # The close is not known at next-open execution; only the open
                # and tradability flags can gate entry (future-data cutoff).
                reason = self._execution_block(row, "buy", kind)
                if reason:
                    warnings.append(f"entry not executed for {symbol} on {day} ({reason})")
                    execution_events.append(self._execution_event(day, symbol, "buy", "cancelled", reason))
                else:
                    price = float(row["open"]) * (1 + self.slippage_bps / 10000)
                    quantity = self.fee_rules.quantity(cash, price, day, kind, self.lot_size)
                    if quantity > 0:
                        notional = quantity * price
                        entry_costs = self.fee_rules.calculate(notional, day, kind, "buy")
                        commission, transfer = entry_costs.commission, entry_costs.transfer_fee
                        cash -= notional + commission + transfer
                        execution_events.append(self._execution_event(day, symbol, "buy", "filled", "",
                            price, quantity, commission, 0.0, transfer))
                        initial_close = None
                        if self._valid_prices(row, "close"):
                            initial_close = float(row["close"])
                        position = {"symbol": symbol, "quantity": quantity, "entry_price": price,
                                    "signal_date": signal_day, "entry_date": day,
                                    "entry_fees": commission + transfer, "entry_commission": commission,
                                    "entry_transfer": transfer, "last_close": initial_close,
                                    "missing_price_warned": False}
                        exit_idx = day_index + self.holding_period_days
                        pending_exit_date = dates[exit_idx] if exit_idx < len(dates) else None
                    else:
                        warnings.append(f"entry not executed for {symbol} on {day} (insufficient cash)")
                        execution_events.append(self._execution_event(day, symbol, "buy", "cancelled", "insufficient_cash"))

            if position is not None and pending_exit_date is not None and day >= pending_exit_date:
                row = self._row(today, position["symbol"])
                kind = self._instrument_type(position["symbol"], day)
                reason = self._execution_block(row, "sell", kind)
                if reason:
                    warnings.append(f"exit deferred for {position['symbol']} on {day} ({reason})")
                    execution_events.append(self._execution_event(day, position["symbol"], "sell", "deferred",
                        reason, quantity=position["quantity"]))
                else:
                    price = float(row["open"]) * (1 - self.slippage_bps / 10000)
                    notional = position["quantity"] * price
                    exit_costs = self.fee_rules.calculate(notional, day, kind, "sell")
                    commission, tax, transfer = exit_costs.commission, exit_costs.stamp_duty, exit_costs.transfer_fee
                    cash += notional - commission - tax - transfer
                    fees = position["entry_fees"] + commission + tax + transfer
                    execution_events.append(self._execution_event(day, position["symbol"], "sell", "filled", "",
                        price, position["quantity"], commission, tax, transfer))
                    gross = (price - position["entry_price"]) * position["quantity"]
                    trades.append(Trade(position["signal_date"], position["entry_date"], day,
                                        position["symbol"], position["quantity"], position["entry_price"],
                                        price, fees, gross - fees, "holding period",
                                        position["entry_commission"] + commission, tax, position["entry_transfer"] + transfer))
                    position = None
                    pending_exit_date = None

            mark = 0.0
            if position is not None:
                row = self._row(today, position["symbol"])
                if row is not None and self._valid_prices(row, "close"):
                    position["last_close"] = float(row["close"])
                elif (row is not None or self.instrument_types is not None) and not position["missing_price_warned"]:
                    warnings.append(f"cannot mark open position {position['symbol']}: missing or non-finite close")
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
                    self._instrument_type(selection.symbol, day)
                    pending_entry = (dates[day_index + 1], selection.symbol, day)
            elif position is None and pending_entry is None and day_index == len(dates) - 1:
                # A final-day signal cannot be executed within the supplied data.
                selection = strategy.select(day, market, frame[frame["date"] <= day].copy())
                if selection is not None:
                    self._instrument_type(selection.symbol, day)
                    warnings.append(f"incomplete trade: signal on {day} has no next trading day")

        if position is not None:
            warnings.append(f"incomplete trade: open position {position['symbol']} has no executable exit")
        return BacktestResult(trades, equity, warnings, events, execution_events)

    def _market_state(self, frame: pd.DataFrame, day: date) -> MarketState:
        return self._market_state_with_warning(frame, day)[0]

    def _market_state_with_warning(self, frame, day):
        return market_state(frame, day, self.index_symbol, self.trigger_level,
                            self.trigger_return_threshold, self.min_declining_count)

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
        """旧入口只做代理，费用定义集中于 FeeRules。"""
        return self.fee_rules.commission(notional)

    def _quantity(self, cash: float, price: float) -> float:
        """兼容旧调用；未分类证券的预算委托费用模块，不含日期规则。"""
        return self.fee_rules.quantity(cash, price, date.min, None, self.lot_size)

    def _instrument_type(self, symbol: str, day: date) -> str | None:
        if self.instrument_types is None:
            return None
        if symbol not in self.instrument_types:
            raise ValueError(f"unknown instrument type for selected symbol: {symbol}")
        kind = self.instrument_types[symbol]
        self.fee_rules.validate_instrument(kind, day)
        return kind

    def _execution_block(self, row, side: str, kind: str | None) -> str:
        return execution_block(self.status_provider.read(row), side, kind)

    @staticmethod
    def _execution_event(day, symbol, side, status, reason, price=None, quantity=0.0,
                         commission=0.0, stamp_duty=0.0, transfer_fee=0.0):
        return dict(date=day, symbol=symbol, side=side, status=status, reason=reason,
                    price=price, quantity=quantity, commission=commission,
                    stamp_duty=stamp_duty, transfer_fee=transfer_fee)
