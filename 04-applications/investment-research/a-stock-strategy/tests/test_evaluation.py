from datetime import date
import math
from statistics import stdev

import pytest

from strategy.backtest import BacktestResult
from strategy.domain import EquityPoint, Trade
from strategy.evaluation import evaluate


def point(day: int, equity: float, cash: float, position_value: float) -> EquityPoint:
    return EquityPoint(date(2026, 1, day), cash, position_value, equity, 0.0)


def trade(pnl: float) -> Trade:
    return Trade(date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3),
                 "AAA", 1.0, 100.0, 100.0, pnl=pnl)


def test_evaluate_calculates_returns_trades_drawdown_volatility_and_sharpe():
    equity = [
        point(1, 1000.0, 1000.0, 0.0),
        point(2, 1100.0, 100.0, 1000.0),
        point(3, 990.0, 50.0, 940.0),
        point(4, 1200.0, 1200.0, 0.0),
    ]
    result = BacktestResult([trade(100.0), trade(-50.0), trade(0.0)], equity, [])

    metrics = evaluate(result)
    daily_returns = [0.1, 990.0 / 1100.0 - 1.0, 1200.0 / 990.0 - 1.0]

    assert metrics.cumulative_return == pytest.approx(0.2)
    assert metrics.annualized_return == pytest.approx(1.2 ** (365 / 3) - 1)
    assert metrics.win_rate == pytest.approx(1 / 3)
    assert metrics.average_profit == pytest.approx(100.0)
    assert metrics.average_loss == pytest.approx(-50.0)
    assert metrics.profit_factor == pytest.approx(2.0)
    assert metrics.max_drawdown == pytest.approx(-0.1)
    assert metrics.annualized_volatility == pytest.approx(stdev(daily_returns) * math.sqrt(252))
    assert metrics.sharpe_ratio == pytest.approx(
        (sum(daily_returns) / len(daily_returns)) / stdev(daily_returns) * math.sqrt(252)
    )
    assert metrics.trade_count == 3
    assert metrics.cash_ratio == pytest.approx(0.5)


def test_benchmark_return_uses_only_dates_shared_with_strategy_equity():
    strategy_equity = [point(1, 100.0, 100.0, 0.0), point(2, 110.0, 0.0, 110.0),
                       point(3, 105.0, 0.0, 105.0), point(4, 120.0, 120.0, 0.0)]
    benchmark = [
        point(1, 100.0, 100.0, 0.0),
        point(2, 105.0, 105.0, 0.0),
        point(4, 120.0, 120.0, 0.0),
        point(5, 130.0, 130.0, 0.0),
    ]

    metrics = evaluate(BacktestResult([], strategy_equity, []), benchmark)

    assert metrics.benchmark_return == pytest.approx(0.2)
    assert metrics.excess_return == pytest.approx(0.0)


def test_excess_return_uses_strategy_return_over_the_shared_period():
    strategy_equity = [point(1, 100.0, 100.0, 0.0), point(2, 110.0, 0.0, 110.0),
                       point(3, 115.0, 0.0, 115.0), point(4, 120.0, 120.0, 0.0)]
    benchmark = [point(2, 105.0, 105.0, 0.0), point(4, 120.0, 120.0, 0.0)]

    metrics = evaluate(BacktestResult([], strategy_equity, []), benchmark)

    expected_strategy = 120.0 / 110.0 - 1.0
    expected_benchmark = 120.0 / 105.0 - 1.0
    assert metrics.excess_return == pytest.approx(expected_strategy - expected_benchmark)


def test_extreme_finite_pnl_values_do_not_overflow_trade_metrics():
    metrics = evaluate(BacktestResult([trade(1e308), trade(1e308), trade(-1e-308)],
                                      [point(1, 100.0, 100.0, 0.0), point(2, 100.0, 100.0, 0.0)], []))

    assert math.isfinite(metrics.average_profit)
    assert math.isfinite(metrics.average_loss)
    assert math.isfinite(metrics.profit_factor)


def test_extreme_finite_equity_returns_have_finite_volatility_and_sharpe():
    equity = [point(1, 1.0, 1.0, 0.0), point(2, 1e308, 1e308, 0.0),
              point(3, 1.0, 1.0, 0.0)]

    metrics = evaluate(BacktestResult([], equity, []))

    assert math.isfinite(metrics.annualized_volatility)
    assert math.isfinite(metrics.sharpe_ratio)


def test_invalid_pnl_trades_are_excluded_from_win_rate_denominator():
    metrics = evaluate(BacktestResult([trade(100.0), trade(float("nan")), trade(-50.0)],
                                      [point(1, 100.0, 100.0, 0.0), point(2, 100.0, 100.0, 0.0)], []))

    assert metrics.win_rate == pytest.approx(0.5)
    assert metrics.trade_count == 3


def test_risk_free_rate_changes_sharpe_ratio():
    equity = [point(1, 100.0, 100.0, 0.0), point(2, 110.0, 0.0, 110.0),
              point(3, 99.0, 99.0, 0.0)]
    result = BacktestResult([], equity, [])

    no_risk_free = evaluate(result, risk_free_rate=0.0)
    with_risk_free = evaluate(result, risk_free_rate=0.25)

    assert with_risk_free.sharpe_ratio < no_risk_free.sharpe_ratio


def test_empty_and_one_point_results_have_explicit_finite_defaults():
    empty = evaluate(BacktestResult([], [], []))
    one = evaluate(BacktestResult([], [point(1, 100.0, 100.0, 0.0)], []))

    for metrics in (empty, one):
        assert metrics.cumulative_return == 0.0
        assert metrics.annualized_return == 0.0
        assert metrics.win_rate == 0.0
        assert metrics.average_profit == 0.0
        assert metrics.average_loss == 0.0
        assert metrics.profit_factor == 0.0
        assert metrics.max_drawdown == 0.0
        assert metrics.annualized_volatility == 0.0
        assert metrics.sharpe_ratio == 0.0
        assert metrics.trade_count == 0
        assert metrics.cash_ratio == 1.0
        assert metrics.benchmark_return is None
        assert metrics.excess_return is None
