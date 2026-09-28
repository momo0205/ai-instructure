from datetime import date, timedelta

import pandas as pd
import pytest

from strategy.backtest import BacktestEngine
from strategy.domain import Selection


def bars(start='2023-08-25', count=5):
    return pd.DataFrame([dict(date=date.fromisoformat(start)+timedelta(days=i), symbol='AAA',
        open=10., high=10., low=10., close=10., volume=100, amount=1000,
        is_suspended=False, limit_up=False, limit_down=False) for i in range(count)])


class Signals:
    def select(self, day, market, universe):
        return Selection('AAA', 1) if day == universe.date.min() else None


def engine(**kw):
    return BacktestEngine(initial_cash=10005, slippage_bps=0, instrument_types={'AAA':'stock'}, **kw)


@pytest.mark.parametrize('start,rate', [('2023-08-25', .001), ('2023-08-26', .0005)])
def test_stock_tax_date_and_budget(start, rate):
    result = engine().run(bars(start, 3), Signals())
    trade = result.trades[0]
    assert trade.quantity == 900  # 1000 shares plus minimum commission and transfer exceeds cash.
    assert trade.stamp_duty == pytest.approx(9000*rate)
    assert trade.transfer_fee == pytest.approx(.18)
    assert trade.commission == 10
    assert trade.fees == pytest.approx(trade.commission+trade.stamp_duty+trade.transfer_fee)
    assert trade.pnl == pytest.approx(-trade.fees)
    assert all(p.cash >= 0 for p in result.equity)
    assert trade.exit_date > trade.entry_date
    assert [e['status'] for e in result.execution_events] == ['filled','filled']


@pytest.mark.parametrize('flag,reason', [('is_suspended','suspended'), ('limit_up','limit_up')])
def test_stock_cancelled_entry(flag, reason):
    frame = bars(); frame.loc[1, flag] = True
    result = engine().run(frame, Signals())
    assert not result.trades
    assert result.execution_events[0]['status'] == 'cancelled'
    assert result.execution_events[0]['reason'] == reason


def test_limit_down_can_buy_but_defers_sell():
    frame = bars(); frame.loc[[1,2,3], 'limit_down'] = True
    result = engine().run(frame, Signals())
    assert result.trades[0].exit_date == frame.iloc[4].date
    assert [e['status'] for e in result.execution_events] == ['filled','deferred','deferred','filled']


@pytest.mark.parametrize('missing', [True,False])
def test_missing_or_invalid_open_defers_exit(missing):
    frame = bars()
    if missing: frame.loc[2,'symbol'] = 'OTHER'
    else: frame.loc[2,'open'] = float('nan')
    result = engine().run(frame, Signals())
    assert result.execution_events[1]['reason'] == ('missing_row' if missing else 'invalid_open')
    assert result.trades[0].exit_date == frame.iloc[3].date
    assert result.warnings


def test_etf_explicit_mapping_preserves_zero_tax_legacy_results():
    frame = bars()
    options = dict(initial_cash=10005, slippage_bps=0, stamp_duty_rate=0, lot_size=100)
    old = BacktestEngine(**options).run(frame, Signals())
    new = BacktestEngine(**options, instrument_types={'AAA':'etf'}).run(frame, Signals())
    assert old.trades == new.trades
    assert old.equity == new.equity
    assert new.trades[0].transfer_fee == new.trades[0].stamp_duty == 0


def test_reject_unknown_and_unsupported_history():
    with pytest.raises(ValueError, match='instrument'):
        BacktestEngine(10000, instrument_types={}).run(bars(), Signals())
    with pytest.raises(ValueError, match='2022-07-01'):
        engine().run(bars('2022-06-28'), Signals())


def test_mixed_fees_follow_selected_symbol():
    frame = bars(count=6)
    second = frame.copy(); second.symbol = 'ETF'
    frame = pd.concat([frame, second], ignore_index=True).sort_values("date").reset_index(drop=True)
    class Mixed:
        def select(self, day, market, universe):
            index = (day-date(2023,8,25)).days
            return Selection('AAA' if index == 0 else 'ETF',1) if index in (0,2) else None
    result = BacktestEngine(20000, slippage_bps=0, lot_size=100,
        instrument_types={'AAA':'stock','ETF':'etf'}).run(frame, Mixed())
    assert len(result.trades) == 2
    assert result.trades[0].stamp_duty > 0
    assert result.trades[1].stamp_duty == result.trades[1].transfer_fee == 0


@pytest.mark.parametrize('missing', [True, False])
def test_missing_or_invalid_entry_is_cancelled(missing):
    frame = bars()
    if missing:
        frame.loc[1, 'symbol'] = 'OTHER'
    else:
        frame.loc[1, 'open'] = float('nan')
    result = engine().run(frame, Signals())
    assert not result.trades
    assert result.execution_events[0]['status'] == 'cancelled'
    assert result.execution_events[0]['reason'] == ('missing_row' if missing else 'invalid_open')


def test_zero_daily_volume_does_not_infer_open_suspension():
    frame = bars()
    frame.loc[1, ['volume', 'amount']] = 0
    result = engine().run(frame, Signals())
    assert result.trades[0].entry_date == frame.iloc[1].date


def test_mapped_etf_keeps_limit_down_entry_gate():
    frame = bars(); frame.loc[1, 'limit_down'] = True
    result = BacktestEngine(10000, instrument_types={'AAA': 'etf'}).run(frame, Signals())
    assert not result.trades
    assert result.execution_events[0]['reason'] == 'limit_down'


def test_engine_uses_injected_status_provider():
    from strategy.tradability import TradingStatus
    class SuspendedProvider:
        def read(self, row):
            return TradingStatus(True, True, suspended=True, source='test-status')
    result=engine(status_provider=SuspendedProvider()).run(bars(),Signals())
    assert not result.trades
    assert result.execution_events[0]['reason']=='suspended'
