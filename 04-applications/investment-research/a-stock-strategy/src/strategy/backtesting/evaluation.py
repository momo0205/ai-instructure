"""Deterministic performance metrics for backtest results."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import math
import sys
from typing import Any

from strategy.backtesting.engine import BacktestResult
from strategy.domain import EquityPoint, Trade


TRADING_DAYS_PER_YEAR = 252.0
CALENDAR_DAYS_PER_YEAR = 365.0
MAX_FINITE = sys.float_info.max


@dataclass(frozen=True, slots=True)
class Metrics:
    """Summary statistics calculated from a :class:`BacktestResult`.

    Return and drawdown values are decimal fractions (``0.10`` means 10%).
    ``max_drawdown`` is negative, matching ``EquityPoint.drawdown``.  A
    benchmark is optional; its two comparison fields are ``None`` when no
    benchmark was supplied.
    """

    cumulative_return: float = 0.0
    annualized_return: float = 0.0
    win_rate: float = 0.0
    average_profit: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    annualized_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    trade_count: int = 0
    cash_ratio: float = 1.0
    benchmark_return: float | None = None
    excess_return: float | None = None

    # Small aliases make the object convenient for callers that use shorter
    # names without duplicating state or changing the serialized field names.
    @property
    def avg_profit(self) -> float:
        return self.average_profit

    @property
    def avg_loss(self) -> float:
        return self.average_loss

    @property
    def sharpe(self) -> float:
        return self.sharpe_ratio

    @property
    def volatility(self) -> float:
        return self.annualized_volatility


def evaluate(
    result: BacktestResult,
    benchmark_equity: Iterable[Any] | Mapping[Any, Any] | None = None,
    risk_free_rate: float = 0.0,
) -> Metrics:
    """Calculate stable performance and optional benchmark metrics.

    ``benchmark_equity`` accepts the same dated ``EquityPoint`` sequence as
    ``result.equity``.  A mapping or sequence of ``(date, value)`` pairs is
    also accepted for callers that store a benchmark as a plain series.  The
    benchmark return uses the first and last dates shared with strategy
    equity, preventing unmatched leading/trailing observations from changing
    the comparison.
    """
    risk_free_rate = _finite_rate(risk_free_rate)
    equity = _equity_by_date(result.equity)
    values = list(equity.values())

    cumulative_return = _return(values[0], values[-1]) if len(values) > 1 else 0.0
    annualized_return = _annualized_return(equity) if len(equity) > 1 else 0.0
    daily_returns = _returns(values)
    annualized_volatility = _annualized_volatility(daily_returns)
    sharpe_ratio = _sharpe_ratio(daily_returns, risk_free_rate)
    max_drawdown = _max_drawdown(values)

    trades = list(result.trades)
    pnls = [_finite_number(trade.pnl) for trade in trades]
    pnls = [pnl for pnl in pnls if pnl is not None]
    profits = [pnl for pnl in pnls if pnl > 0.0]
    losses = [pnl for pnl in pnls if pnl < 0.0]
    average_profit = _safe_mean(profits)
    average_loss = _safe_mean(losses)
    gross_profit = _safe_sum(profits)
    gross_loss = -_safe_sum(losses)
    # Returning zero for an undefined ratio keeps empty/all-flat results
    # finite and serializable.  A positive-only run has no observed loss from
    # which to estimate a profit factor, so it is treated as undefined too.
    profit_factor = _safe_ratio(gross_profit, gross_loss)

    benchmark_return: float | None = None
    excess_return: float | None = None
    if benchmark_equity is not None:
        benchmark = _equity_by_date(benchmark_equity)
        shared_dates = sorted(set(equity).intersection(benchmark))
        if len(shared_dates) > 1:
            strategy_return = _return(equity[shared_dates[0]], equity[shared_dates[-1]])
            benchmark_return = _return(benchmark[shared_dates[0]], benchmark[shared_dates[-1]])
            excess_return = strategy_return - benchmark_return
        else:
            benchmark_return = 0.0
            excess_return = cumulative_return - benchmark_return

    return Metrics(
        cumulative_return=cumulative_return,
        annualized_return=annualized_return,
        win_rate=(len(profits) / len(pnls)) if pnls else 0.0,
        average_profit=average_profit,
        average_loss=average_loss,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
        annualized_volatility=annualized_volatility,
        sharpe_ratio=sharpe_ratio,
        trade_count=len(trades),
        cash_ratio=_cash_ratio(result.equity),
        benchmark_return=benchmark_return,
        excess_return=excess_return,
    )


def _finite_rate(value: Any) -> float:
    try:
        rate = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("risk_free_rate must be finite") from exc
    if not math.isfinite(rate):
        raise ValueError("risk_free_rate must be finite")
    if rate < -1.0:
        raise ValueError("risk_free_rate must be at least -1")
    return rate


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _safe_sum(values: Sequence[float]) -> float:
    """Sum finite values while saturating overflow at the largest float."""
    if not values:
        return 0.0
    try:
        total = math.fsum(values)
    except OverflowError:
        scale = max(abs(value) for value in values)
        if scale == 0.0:
            return 0.0
        # Scaling before summing preserves cancellation while keeping every
        # intermediate within a manageable range.
        scaled = math.fsum(value / scale for value in values)
        total = scaled * scale
    if math.isfinite(total):
        return total
    return math.copysign(MAX_FINITE, total)


def _safe_mean(values: Sequence[float]) -> float:
    return _safe_sum(values) / len(values) if values else 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return 0.0
    ratio = numerator / denominator
    return ratio if math.isfinite(ratio) else MAX_FINITE


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        # Keep pandas out of this module's implementation; date-like objects
        # (including pandas Timestamp) expose a date() method.
        converted = value.date()
    except (AttributeError, TypeError, ValueError):
        return None
    return converted if isinstance(converted, date) else None


def _equity_by_date(equity: Iterable[Any] | Mapping[Any, Any]) -> dict[date, float]:
    """Normalize dated equity into sorted, finite, last-observation values."""
    observations: Iterable[Any]
    if isinstance(equity, Mapping) or callable(getattr(equity, "items", None)):
        observations = equity.items()
    else:
        observations = equity

    normalized: dict[date, float] = {}
    for observation in observations:
        if isinstance(observation, EquityPoint):
            raw_day, raw_value = observation.date, observation.equity
        elif isinstance(observation, (tuple, list)) and len(observation) == 2:
            raw_day, raw_value = observation
        else:
            # A duck-typed EquityPoint keeps this helper usable with an
            # equivalent immutable domain object without accepting bare values
            # that cannot be aligned by date.
            raw_day = getattr(observation, "date", None)
            raw_value = getattr(observation, "equity", None)
        day = _as_date(raw_day)
        value = _finite_number(raw_value)
        if day is not None and value is not None:
            normalized[day] = value
    return dict(sorted(normalized.items()))


def _return(initial: float, final: float) -> float:
    if initial <= 0.0:
        return 0.0
    if final <= 0.0:
        return -1.0
    # expm1(log(final) - log(initial)) is more accurate for small returns
    # than final / initial - 1 and avoids unnecessary intermediate overflow.
    try:
        return math.expm1(math.log(final) - math.log(initial))
    except (OverflowError, ValueError):
        return 0.0


def _annualized_return(equity: Mapping[date, float]) -> float:
    first, last = next(iter(equity.items())), next(reversed(equity.items()))
    elapsed_days = (last[0] - first[0]).days
    if elapsed_days <= 0:
        return 0.0
    if first[1] <= 0.0:
        return 0.0
    if last[1] <= 0.0:
        return -1.0
    try:
        return math.expm1((math.log(last[1]) - math.log(first[1])) * CALENDAR_DAYS_PER_YEAR / elapsed_days)
    except (OverflowError, ValueError):
        return 0.0


def _returns(values: Sequence[float]) -> list[float]:
    returns: list[float] = []
    for previous, current in zip(values, values[1:]):
        if previous <= 0.0:
            continue
        returns.append(_return(previous, current))
    return returns


def _sample_std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    scale = max(abs(value) for value in values)
    if scale == 0.0:
        return 0.0
    # Apply Welford's one-pass algorithm to scaled values.  Scaling avoids
    # overflowing the squared delta for large, but still finite, returns.
    mean = 0.0
    sum_squared_deltas = 0.0
    for count, value in enumerate(values, 1):
        scaled_value = value / scale
        delta = scaled_value - mean
        mean += delta / count
        sum_squared_deltas += delta * (scaled_value - mean)
    standard_deviation = math.sqrt(max(0.0, sum_squared_deltas / (len(values) - 1))) * scale
    return standard_deviation if math.isfinite(standard_deviation) else MAX_FINITE


def _annualized_volatility(daily_returns: Sequence[float]) -> float:
    volatility = _sample_std(daily_returns)
    annualized = volatility * math.sqrt(TRADING_DAYS_PER_YEAR)
    return annualized if math.isfinite(annualized) else MAX_FINITE


def _sharpe_ratio(daily_returns: Sequence[float], annual_risk_free_rate: float) -> float:
    if len(daily_returns) < 2:
        return 0.0
    daily_risk_free = -1.0 if annual_risk_free_rate == -1.0 else math.expm1(
        math.log1p(annual_risk_free_rate) / TRADING_DAYS_PER_YEAR
    )
    excess = [value - daily_risk_free for value in daily_returns]
    volatility = _sample_std(daily_returns)
    if not volatility:
        return 0.0
    sharpe = _safe_mean(excess) / volatility * math.sqrt(TRADING_DAYS_PER_YEAR)
    return sharpe if math.isfinite(sharpe) else math.copysign(MAX_FINITE, sharpe)


def _max_drawdown(values: Sequence[float]) -> float:
    peak = 0.0
    maximum = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0.0:
            # Long-only equity cannot lose more than its full value.  Clamping
            # nonpositive values also prevents invalid negative equity from
            # producing an unbounded or non-finite percentage drawdown.
            drawdown = -1.0 if value <= 0.0 else value / peak - 1.0
            maximum = min(maximum, drawdown)
    return maximum


def _cash_ratio(equity: Iterable[EquityPoint]) -> float:
    points = list(equity)
    if not points:
        return 1.0
    valid = 0
    cash_days = 0
    for point in points:
        position_value = _finite_number(getattr(point, "position_value", None))
        if position_value is None:
            continue
        valid += 1
        if position_value == 0.0:
            cash_days += 1
    return cash_days / valid if valid else 1.0
