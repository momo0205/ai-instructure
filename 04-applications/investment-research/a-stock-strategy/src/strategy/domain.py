from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class MarketState:
    as_of: date
    index_level: float
    index_return_1d: float
    triggered: bool
    declining_count: int | None = None


@dataclass(frozen=True, slots=True)
class Selection:
    symbol: str
    score: float
    features: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass(frozen=True, slots=True)
class Trade:
    signal_date: date
    entry_date: date
    exit_date: date | None
    symbol: str
    quantity: float
    entry_price: float
    exit_price: float | None
    fees: float = 0.0
    pnl: float = 0.0
    exit_reason: str = ""
    commission: float = 0.0
    stamp_duty: float = 0.0
    transfer_fee: float = 0.0


@dataclass(frozen=True, slots=True)
class EquityPoint:
    date: date
    cash: float
    position_value: float
    equity: float
    drawdown: float

