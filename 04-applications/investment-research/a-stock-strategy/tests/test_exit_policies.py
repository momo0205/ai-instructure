from dataclasses import asdict
from datetime import date

import pandas as pd
import pytest

from strategy.backtesting.engine import BacktestEngine
from strategy.domain import Selection


def market(closes):
    return pd.DataFrame([dict(date=date(2026, 1, i+1), symbol='AAA', open=10., high=max(10., c),
        low=min(10., c), close=c, volume=100, amount=1000, is_suspended=False,
        limit_up=False, limit_down=False) for i,c in enumerate(closes)])


class Once:
    def __init__(self, signal=date(2026, 1, 1)):
        self.signal = signal
    def select(self, as_of, market, universe):
        return Selection('AAA', 1) if as_of == self.signal else None


def engine(window=2, maximum=20, **kwargs):
    return BacktestEngine(1000, commission_rate=0, stamp_duty_rate=0, minimum_commission=0,
        slippage_bps=0, exit_policy={'id':'close_below_sma', 'parameters':{
            'window':window, 'max_holding_days':maximum}}, **kwargs)


def test_buy_day_close_signal_sells_next_open_and_prepared_parity():
    frame = market([12, 8, 20, 20])
    runner = engine()
    result = runner.run(frame, Once())
    assert result.trades[0].exit_date == date(2026, 1, 3)
    assert result.trades[0].exit_reason == 'close_below_sma'
    event = result.exit_decision_events[0]
    assert (event['sma'], event['close'], event['held_sessions']) == (10, 8, 0)
    assert event['exit_signal_date'] == date(2026, 1, 2)
    assert asdict(result) == asdict(runner.run_prepared(runner.prepare_market(frame), Once()))


@pytest.mark.parametrize('block', ['limit_down', 'is_suspended', 'open'])
def test_pending_signal_is_not_cancelled_by_recovery(block):
    frame = market([12, 8, 20, 20])
    frame.loc[2, block] = float('nan') if block == 'open' else True
    result = engine().run(frame, Once())
    assert result.trades[0].exit_date == date(2026, 1, 4)
    assert result.exit_decision_events[1]['status'] == 'pending'
    assert result.execution_events[-1]['exit_signal_date'] == date(2026, 1, 2)


def test_equal_does_not_trigger_and_maximum_forces_open_exit():
    result = engine(maximum=2).run(market([10]*5), Once())
    assert result.trades[0].exit_date == date(2026, 1, 4)
    assert result.trades[0].exit_reason == 'max_holding_days'
    assert not any(e['status']=='triggered' for e in result.exit_decision_events)


def test_end_signal_preserved_without_invented_execution_day():
    result = engine().run(market([12, 8]), Once())
    assert not result.trades
    assert result.exit_decision_events[-1]['status'] == 'triggered'
    assert result.exit_decision_events[-1]['planned_exit_date'] is None


def test_warmup_and_missing_day_are_not_skipped():
    frame = market([20, 20, 20, 10, 10])
    result = engine(window=4).run(frame, Once(date(2026, 1, 3)), start=date(2026, 1, 3))
    assert result.exit_decision_events[0]['sma'] == 17.5
    frame.loc[1, 'symbol'] = 'BBB'
    result = engine(window=4).run(frame, Once(date(2026, 1, 3)), start=date(2026, 1, 3))
    assert result.exit_decision_events[0]['status'] == 'indicator_unavailable'
    assert result.exit_decision_events[0]['available'] == 3


def test_future_prices_do_not_change_prior_evidence():
    frame = market([12, 8, 20, 20])
    prior = engine().run(frame, Once()).exit_decision_events[0]
    frame.loc[3, ['close','high']] = 999
    assert engine().run(frame, Once()).exit_decision_events[0] == prior


def test_suspended_day_never_creates_new_close_signal():
    frame = market([12, 12, 8, 12, 12])
    frame.loc[2,'is_suspended'] = True
    result = engine().run(frame, Once())
    assert not result.trades
    assert result.exit_decision_events[1]['reason'] == 'suspended'


def test_fixed_explicit_and_legacy_are_identical():
    frame = market([12, 8, 20, 20])
    old = BacktestEngine(1000, holding_period_days=2).run(frame, Once())
    explicit = BacktestEngine(1000, holding_period_days=2, exit_policy={'id':'fixed_holding'}).run(frame, Once())
    assert asdict(old) == asdict(explicit)
    assert old.trades[0].exit_reason == 'holding period'


@pytest.mark.parametrize('value', [False, [], {'id':'unknown'}, {'id':[]}, {'extra':1},
    {'id':'fixed_holding','parameters':{'window':2}},
    {'id':'close_below_sma','parameters':{'window':True}},
    {'id':'close_below_sma','parameters':{'window':1}},
    {'id':'close_below_sma','parameters':{'max_holding_days':253}}])
def test_invalid_policy_rejected(value):
    from strategy.exit_policies import normalize_exit_policy
    from strategy.validation import UserError
    with pytest.raises(UserError) as error:
        normalize_exit_policy(value)
    assert error.value.code == 'INVALID_REQUEST'


def test_defaults_and_catalog():
    from strategy.exit_policies import normalize_exit_policy, exit_policy_catalog
    assert normalize_exit_policy(None) == {'id':'fixed_holding','parameters':{}}
    assert normalize_exit_policy({'id':'close_below_sma'})['parameters'] == {'window':20,'max_holding_days':20}
    assert [p['id'] for p in exit_policy_catalog()] == ['fixed_holding','close_below_sma']


def test_sma_intent_wins_when_next_open_also_reaches_maximum():
    result = engine(maximum=1).run(market([12, 8, 20]), Once())
    assert result.trades[0].exit_reason == 'close_below_sma'
    sell = result.execution_events[-1]
    assert sell['max_holding_reached'] is True
    assert sell['exit_signal_date'] == date(2026, 1, 2)


def test_unavailable_indicator_never_blocks_maximum_exit():
    result = engine(window=20, maximum=1).run(market([12, 8, 20]), Once())
    assert result.exit_decision_events[0]['available'] == 2
    assert result.exit_decision_events[0]['status'] == 'indicator_unavailable'
    assert result.trades[0].exit_reason == 'max_holding_days'
    assert result.execution_events[-1]['exit_signal_date'] is None


def test_no_entry_has_no_exit_evidence():
    result = engine().run(market([12, 8, 20]), Once(date(2025, 1, 1)))
    assert result.exit_decision_events == []
    assert result.trades == []


def test_indicator_uses_only_requested_symbol_and_asof():
    from strategy.indicators import simple_moving_average
    frame = market([2, 4, 6, 999])
    other = frame.copy()
    other['symbol'] = 'BBB'
    other['close'] = 10000
    frame = pd.concat([frame, other])
    value = simple_moving_average(frame, 'AAA', date(2026, 1, 3), 3)
    assert (value.value, value.available) == (4, 3)


def test_old_long_holding_period_remains_accepted():
    runner = BacktestEngine(1000, holding_period_days=300)
    assert runner.exit_policy.holding_days == 300


def test_pending_day_does_not_present_old_indicator_as_current():
    frame = market([12, 8, 20, 20])
    frame.loc[2, 'limit_down'] = True
    result = engine().run(frame, Once())
    pending = result.exit_decision_events[1]
    assert pending['status'] == 'pending'
    assert pending['close'] is None and pending['sma'] is None
    assert pending['exit_signal_date'] == date(2026, 1, 2)
