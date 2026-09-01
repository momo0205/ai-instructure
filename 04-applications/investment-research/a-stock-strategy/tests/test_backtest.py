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


def test_sparse_daily_rows_keep_last_known_close_for_mark_to_market():
    frame = bars((date(2026, 1, 1), "AAA", 10, 10), (date(2026, 1, 2), "AAA", 11, 11),
                 (date(2026, 1, 3), "BBB", 20, 20), (date(2026, 1, 4), "AAA", 12, 12))
    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0,
                            minimum_commission=0, slippage_bps=0).run(frame, AlwaysSelect())
    position = result.equity[2]
    assert position.position_value == result.trades[0].quantity * 11
    assert position.equity == position.cash + position.position_value


def test_cost_parameters_must_be_non_negative():
    import pytest
    for name in ("commission_rate", "stamp_duty_rate", "minimum_commission", "slippage_bps"):
        with pytest.raises(ValueError, match="non-negative"):
            BacktestEngine(initial_cash=100, **{name: -1})


def test_cost_parameters_must_be_finite():
    import math
    import pytest
    for name in ("commission_rate", "stamp_duty_rate", "minimum_commission", "slippage_bps"):
        with pytest.raises(ValueError, match="finite"):
            BacktestEngine(initial_cash=100, **{name: math.nan})


def test_initial_cash_and_trigger_parameters_must_be_finite():
    import pytest
    with pytest.raises(ValueError, match="non-negative"):
        BacktestEngine(initial_cash=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        BacktestEngine(initial_cash=100, trigger_level=float("inf"))


def test_non_finite_entry_prices_are_not_executed():
    frame = bars((date(2026, 1, 1), "AAA", 10, 10), (date(2026, 1, 2), "AAA", float("nan"), 11),
                 (date(2026, 1, 3), "AAA", 12, 12))
    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0,
                            minimum_commission=0, slippage_bps=0).run(frame, AlwaysSelect())
    assert not result.trades
    assert any("entry not executed" in warning for warning in result.warnings)


def test_non_finite_close_does_not_poison_mark_to_market():
    frame = bars((date(2026, 1, 1), "AAA", 10, 10), (date(2026, 1, 2), "AAA", 11, 11),
                 (date(2026, 1, 3), "AAA", 12, float("nan")), (date(2026, 1, 4), "AAA", 13, 13))
    result = BacktestEngine(initial_cash=1000, holding_period_days=2, commission_rate=0, stamp_duty_rate=0,
                            minimum_commission=0, slippage_bps=0).run(frame, AlwaysSelect())
    assert result.equity[2].position_value == result.trades[0].quantity * 11
    assert all(pd.notna(point.equity) for point in result.equity)
    assert any("mark" in warning for warning in result.warnings)


def test_non_numeric_entry_close_does_not_crash_or_poison_equity():
    frame = bars((date(2026, 1, 1), "AAA", 10, 10),
                 (date(2026, 1, 2), "AAA", 11, 11),
                 (date(2026, 1, 3), "AAA", 12, 12))
    frame["close"] = frame["close"].astype(object)
    frame.loc[(frame["date"] == date(2026, 1, 2)) & (frame["symbol"] == "AAA"), "close"] = "bad"
    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0,
                            minimum_commission=0, slippage_bps=0).run(frame, AlwaysSelect())
    assert result.trades
    assert all(pd.notna(point.equity) for point in result.equity)
    assert any("mark" in warning for warning in result.warnings)


def test_market_state_fails_closed_when_configured_index_is_missing_or_invalid():
    engine = BacktestEngine(initial_cash=1000, index_symbol="INDEX")
    missing = bars((date(2026, 1, 1), "AAA", 10, 10))
    assert engine._market_state(missing, date(2026, 1, 1)).triggered is False

    malformed = bars((date(2026, 1, 1), "INDEX", 4100, 4100),
                     (date(2026, 1, 2), "INDEX", 4100, float("nan")))
    assert engine._market_state(malformed, date(2026, 1, 2)).triggered is False


def test_run_warns_when_configured_index_history_is_missing_or_invalid():
    missing = bars((date(2026, 1, 1), "AAA", 10, 10), (date(2026, 1, 2), "AAA", 11, 11))
    missing_result = BacktestEngine(initial_cash=1000, index_symbol="INDEX").run(missing, AlwaysSelect())
    assert any("missing market index INDEX" in warning for warning in missing_result.warnings)

    malformed = bars((date(2026, 1, 1), "INDEX", 4100, 4100),
                     (date(2026, 1, 1), "AAA", 10, 10),
                     (date(2026, 1, 2), "INDEX", 4100, float("nan")),
                     (date(2026, 1, 2), "AAA", 11, 11))
    malformed_result = BacktestEngine(initial_cash=1000, index_symbol="INDEX").run(malformed, AlwaysSelect())
    assert any("invalid market index INDEX close" in warning for warning in malformed_result.warnings)

    stale_bad = bars((date(2026, 1, 1), "INDEX", 4100, float("nan")),
                     (date(2026, 1, 1), "AAA", 10, 10),
                     (date(2026, 1, 2), "INDEX", 4100, 4100),
                     (date(2026, 1, 2), "AAA", 11, 11),
                     (date(2026, 1, 3), "INDEX", 4000, 4000),
                     (date(2026, 1, 3), "AAA", 12, 12))
    stale_result = BacktestEngine(initial_cash=1000, index_symbol="INDEX").run(stale_bad, AlwaysSelect())
    assert any("invalid market index INDEX close" in warning for warning in stale_result.warnings)
    assert BacktestEngine(initial_cash=1000, index_symbol="INDEX")._market_state(
        stale_bad, date(2026, 1, 3)
    ).triggered is False


def test_run_rejects_missing_full_market_contract_column():
    frame = bars((date(2026, 1, 1), "AAA", 10, 10)).drop(columns=["high"])
    import pytest
    with pytest.raises(ValueError, match="missing required columns"):
        BacktestEngine(initial_cash=1000).run(frame, AlwaysSelect())


def test_run_rejects_partially_missing_tradability_flags():
    import pytest

    for missing_flags in (("is_suspended",), ("is_suspended", "limit_up")):
        frame = bars((date(2026, 1, 1), "AAA", 10, 10)).drop(columns=list(missing_flags))
        with pytest.raises(ValueError, match="missing tradability columns"):
            BacktestEngine(initial_cash=1000).run(frame, AlwaysSelect())


def test_run_rejects_duplicate_rows_before_strategy_execution():
    frame = bars((date(2026, 1, 1), "AAA", 10, 10), (date(2026, 1, 1), "AAA", 10, 10))
    import pytest
    with pytest.raises(ValueError, match="duplicate date/symbol"):
        BacktestEngine(initial_cash=1000).run(frame, AlwaysSelect())


def test_entry_does_not_use_same_day_close_as_future_data():
    frame = bars((date(2026, 1, 1), "AAA", 10, 10),
                 (date(2026, 1, 2), "AAA", 11, float("nan")),
                 (date(2026, 1, 3), "AAA", 12, 12))
    result = BacktestEngine(initial_cash=1000, commission_rate=0, stamp_duty_rate=0,
                            minimum_commission=0, slippage_bps=0).run(frame, AlwaysSelect())
    assert result.trades and result.trades[0].entry_date == date(2026, 1, 2)


def test_engine_rejects_non_positive_prices_at_entry():
    frame = bars((date(2026, 1, 1), "AAA", 0, 10), (date(2026, 1, 2), "AAA", 11, 11))
    import pytest
    with pytest.raises(ValueError, match="non-finite or non-positive prices"):
        BacktestEngine(initial_cash=1000).run(frame, AlwaysSelect())
