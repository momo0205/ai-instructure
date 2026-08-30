from datetime import date

import pandas as pd

from strategy.backtest import BacktestEngine
from strategy.domain import MarketState, Selection


class AlwaysSelect:
    def __init__(self, symbol="AAA"):
        self.symbol = symbol
        self.as_ofs = []

    def select(self, as_of, market, universe):
        self.as_ofs.append((as_of, universe["date"].max()))
        return Selection(self.symbol, 1.0)


def bars(*rows):
    return pd.DataFrame(
        [
            dict(date=d, symbol=s, open=o, high=o, low=o, close=c, volume=100, amount=10000,
                 is_suspended=False, limit_up=False, limit_down=False)
            for d, s, o, c in rows
        ]
    )


def test_entry_is_next_open_and_default_exit_is_following_open_without_future_data():
    strategy = AlwaysSelect()
    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0, minimum_commission=0, slippage_bps=0).run(
        bars((date(2026, 1, 1), "AAA", 10, 10), (date(2026, 1, 2), "AAA", 11, 11),
             (date(2026, 1, 3), "AAA", 12, 12), (date(2026, 1, 4), "AAA", 13, 13)), strategy
    )
    trade = result.trades[0]
    assert (trade.signal_date, trade.entry_date, trade.exit_date) == (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3))
    assert trade.entry_price == 11 and trade.exit_price == 12
    assert all(as_of == seen_max for as_of, seen_max in strategy.as_ofs)


def test_suspended_or_limit_up_entry_and_limit_down_exit_do_not_execute():
    frame = bars((date(2026, 1, 1), "AAA", 10, 10), (date(2026, 1, 2), "AAA", 11, 11),
                 (date(2026, 1, 3), "AAA", 12, 12), (date(2026, 1, 4), "AAA", 13, 13))
    frame.loc[frame.date == date(2026, 1, 2), "limit_up"] = True
    frame.loc[frame.date == date(2026, 1, 3), "limit_down"] = True
    class FirstSignal(AlwaysSelect):
        def select(self, as_of, market, universe):
            return super().select(as_of, market, universe) if as_of == date(2026, 1, 1) else None

    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0, minimum_commission=0).run(frame, FirstSignal())
    assert not result.trades
    assert any("entry not executed" in warning for warning in result.warnings)


def test_blocked_exit_is_retried_and_open_position_warns_when_data_ends():
    frame = bars((date(2026, 1, 1), "AAA", 10, 10), (date(2026, 1, 2), "AAA", 11, 11),
                 (date(2026, 1, 3), "AAA", 12, 12), (date(2026, 1, 4), "AAA", 13, 13))
    frame.loc[frame.date == date(2026, 1, 3), "limit_down"] = True
    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0,
                            minimum_commission=0, slippage_bps=0).run(frame, AlwaysSelect())
    assert result.trades[0].exit_date == date(2026, 1, 4)

    short = frame.iloc[:3].copy()
    incomplete = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0,
                                minimum_commission=0, slippage_bps=0).run(short, AlwaysSelect())
    assert any("incomplete" in warning for warning in incomplete.warnings)


def test_cash_position_and_configurable_costs_are_accounted_for():
    result = BacktestEngine(initial_cash=1000, commission_rate=.01, stamp_duty_rate=.02,
                            minimum_commission=0, slippage_bps=100).run(
        bars((date(2026, 1, 1), "AAA", 10, 10), (date(2026, 1, 2), "AAA", 10, 10),
             (date(2026, 1, 3), "AAA", 12, 12)), AlwaysSelect())
    trade = result.trades[0]
    assert trade.entry_price == 10.1 and abs(trade.exit_price - 11.88) < 1e-9
    assert trade.fees > 0 and trade.pnl > 0
    assert result.equity[-1].cash >= 0
