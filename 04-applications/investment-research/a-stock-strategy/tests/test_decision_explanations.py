"""决策留痕须与真实择股一致，并保持下一开盘及固定持有期语义。"""
from datetime import date
from pathlib import Path
import json
import pandas as pd
import pytest
from strategy.domain import MarketState
from strategy.strategies.momentum import MomentumStrategy
from strategy.strategies.qlib_momentum import QlibMomentumStrategy
from strategy.backtesting.engine import BacktestEngine

DAY = date(2024, 1, 3)
STATE = MarketState(DAY, 3000, -.02, True, 4500)


def frame():
    return pd.DataFrame([dict(date=f'2024-01-0{i}', symbol=s, close=p)
        for s, prices in [('A', [10, 11, 12, 100]), ('B', [10, 11, 11, 999])]
        for i, p in enumerate(prices, 1)])


def strategy(cls, symbols=('B', 'A', 'MISSING'), minimum=0):
    result = cls(list(symbols), 2, minimum)
    if cls is QlibMomentumStrategy:
        result.prepared = True
        result.scores = {('2024-01-03', 'A'): .2, ('2024-01-03', 'B'): .1}
    return result


@pytest.mark.parametrize('cls', [MomentumStrategy, QlibMomentumStrategy])
def test_explanation_is_the_selection_and_ignores_future(cls):
    instance = strategy(cls)
    assert callable(getattr(instance, 'evaluate', None)), 'strategy must expose its real evaluation'
    selected, rows = instance.evaluate(DAY, STATE, frame())
    assert selected == instance.select(DAY, STATE, frame())
    assert selected.symbol == 'A'
    by_symbol = {row['symbol']: row for row in rows}
    assert by_symbol['A']['status'] == 'selected'
    assert by_symbol['A']['score'] == pytest.approx(.2)
    assert by_symbol['A']['reference_date'] == '2024-01-01'
    assert by_symbol['A']['reference_close'] == 10
    assert by_symbol['A']['current_close'] == 12
    assert by_symbol['B']['reason'] == 'lower_score'
    assert by_symbol['MISSING']['status'] == 'excluded'
    assert instance.evaluate(DAY, STATE, frame().iloc[::-1]) == (selected, rows)
    json.dumps(rows, allow_nan=False)


@pytest.mark.parametrize('cls', [MomentumStrategy, QlibMomentumStrategy])
def test_exclusions_threshold_tie_and_flags(cls):
    instance = strategy(cls)
    assert hasattr(instance, 'evaluate')
    data = frame()
    data.loc[(data.symbol == 'B') & (data.date == '2024-01-03'), 'close'] = 12
    if cls is QlibMomentumStrategy:
        instance.scores[('2024-01-03', 'B')] = .2
    selected, rows = instance.evaluate(DAY, STATE, data)
    assert selected.symbol == 'A'
    assert next(r for r in rows if r['symbol'] == 'B')['reason'] == 'tie_break'
    instance.minimum_momentum = .3
    assert instance.evaluate(DAY, STATE, data)[0] is None
    assert next(r for r in instance.evaluate(DAY, STATE, data)[1] if r['symbol'] == 'A')['reason'] == 'below_minimum'
    instance.minimum_momentum = 0
    data['is_suspended'] = data.symbol == 'A'
    assert next(r for r in instance.evaluate(DAY, STATE, data)[1] if r['symbol'] == 'A')['reason'] == 'is_suspended'
    data['is_suspended'] = False
    data.loc[(data.symbol == 'A') & (data.date == '2024-01-02'), 'close'] = float('nan')
    row = next(r for r in instance.evaluate(DAY, STATE, data)[1] if r['symbol'] == 'A')
    assert row['reason'] == 'invalid_price'
    json.dumps(row, allow_nan=False)


def market_bars():
    rows = []
    for i in range(1, 8):
        for symbol, price in [('000001.SH', 3000 * .98 ** i), ('A', 10+i)]:
            rows.append(dict(date=f'2024-01-0{i}', symbol=symbol, open=price, high=price,
                low=price, close=price, volume=100, amount=1000, is_suspended=False,
                limit_up=False, limit_down=False, declining_count=4500))
    return pd.DataFrame(rows)


def test_engine_records_holding_and_planned_vs_deferred_exit():
    data = market_bars()
    data.loc[(data.symbol == 'A') & (data.date == '2024-01-05'), 'limit_down'] = True
    instance = MomentumStrategy(['A'], 1, 0)
    result = BacktestEngine(10000, holding_period_days=2, min_declining_count=4000,
        trigger_return_threshold=-.01).run(data, instance)
    assert hasattr(result, 'decision_events'), 'engine must preserve decisions, not reconstruct them'
    decisions = {str(r['date']): r for r in result.decision_events}
    assert decisions['2024-01-01']['status'] == 'market_data_unavailable'
    assert decisions['2024-01-02']['selected_symbol'] == 'A'
    assert str(decisions['2024-01-02']['planned_entry_date']) == '2024-01-03'
    assert decisions['2024-01-03']['status'] == 'holding'
    assert decisions['2024-01-03']['candidates'] == []
    assert decisions['2024-01-03']['position_symbol'] == 'A'
    entries = result.execution_events
    assert entries[0]['signal_date'] == date(2024, 1, 2)
    assert entries[0]['planned_exit_date'] == date(2024, 1, 5)
    assert entries[1]['status'] == 'deferred'
    assert entries[2]['date'] == date(2024, 1, 6)
    assert entries[2]['planned_exit_date'] == date(2024, 1, 5)
    assert entries[2]['signal_date'] == date(2024, 1, 2)


def test_workbench_exports_decisions(tmp_path):
    from strategy import workbench
    result = workbench.execute(Path(__file__).resolve().parents[1],
        {'strategy_id':'price_momentum', 'parameters':{'lookback':2,'minimum_momentum':-1}}, tmp_path)
    assert result.get('decision_events'), 'export must contain decision audit'
    assert len(result['decision_events']) == len(result['equity'])
    selected = [e for e in result['decision_events'] if e['status'] == 'selected']
    assert selected and selected[0]['candidates']
    assert json.loads((tmp_path/'result.json').read_text())['decision_events'] == result['decision_events']


def test_cancelled_buy_has_no_fictional_entry_or_exit():
    result = BacktestEngine(1, min_declining_count=4000, trigger_return_threshold=-.01,
                            lot_size=100).run(market_bars(), MomentumStrategy(['A'], 1, 0))
    first = result.execution_events[0]
    assert first['status'] == 'cancelled'
    assert first['entry_date'] is None and first['planned_exit_date'] is None
    assert first['signal_date'] == date(2024, 1, 2)
    assert first['planned_entry_date'] == date(2024, 1, 3)


def test_final_signal_is_not_an_executable_order():
    data = market_bars()
    result = BacktestEngine(10000, min_declining_count=4000, trigger_return_threshold=-.01).run(
        data, MomentumStrategy(['A'], 1, 0), start=date(2024, 1, 7))
    assert not result.execution_events
    decision = result.decision_events[0]
    assert decision['status'] == 'no_next_session'
    assert decision['selected_symbol'] == 'A' and decision['planned_entry_date'] is None


def test_qlib_uses_real_factor_score_not_a_second_local_calculation():
    instance = strategy(QlibMomentumStrategy, ('A',))
    instance.scores[('2024-01-03', 'A')] = .19999998807907104
    selected, rows = instance.evaluate(DAY, STATE, frame())
    assert rows[0]['score'] == selected.score == .19999998807907104
    instance.scores = {}
    assert instance.evaluate(DAY, STATE, frame())[1][0]['reason'] == 'missing_factor'


def test_select_only_extension_still_works_without_candidate_details():
    from strategy.domain import Selection
    class Extension:
        def select(self, day, market, universe):
            return Selection('A', 1) if day == date(2024, 1, 1) else None
    result = BacktestEngine(10000).run(market_bars(), Extension())
    assert result.trades
    assert result.decision_events[0]['selected_symbol'] == 'A'
    assert result.decision_events[0]['candidate_details_supported'] is False


def test_inherited_evaluate_does_not_bypass_extension_select_override():
    class NoBuy(MomentumStrategy):
        def select(self, day, market, universe):
            return None
    result = BacktestEngine(10000, min_declining_count=4000, trigger_return_threshold=-.01).run(
        market_bars(), NoBuy(['A'], 1, 0))
    assert not result.trades and not result.execution_events
    assert all(not row['candidate_details_supported'] for row in result.decision_events)


def test_missing_market_data_does_not_look_like_zero_return():
    result = BacktestEngine(10000, min_declining_count=4000, trigger_return_threshold=-.01).run(
        market_bars(), MomentumStrategy(['A'], 1, 0))
    first = result.decision_events[0]
    assert first['index_return_1d'] is None
    assert first['market_warning'] and first['status'] == 'market_data_unavailable'
