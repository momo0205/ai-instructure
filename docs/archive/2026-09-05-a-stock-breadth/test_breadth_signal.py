from datetime import date
import pandas as pd
import pytest

from strategy.signals import MarketTrigger
from strategy.backtest import BacktestEngine
from strategy.recommendation import recommend
from strategy.strategies.fixed import FixedAssetStrategy

DAY = date(2026, 8, 4)

def market_frame(count=4200, closes=(3100, 3038, 3060, 3080)):
    rows = []
    for day, close in zip(pd.bdate_range('2026-08-03', periods=4), closes):
        for symbol, price in [('000001.SH', close), ('588000.SH', 1.0)]:
            rows.append(dict(date=day, symbol=symbol, open=price, high=price, low=price,
                close=price, volume=1000, amount=1000, is_suspended=False,
                limit_up=False, limit_down=False, declining_count=count if symbol=='000001.SH' else None,
                eligible_count=5200, observed_count=5200, breadth_complete=True,
                breadth_scope='all_a', breadth_source='synthetic-test'))
    return pd.DataFrame(rows)

@pytest.mark.parametrize('count,ret,want', [(4000,-.02,True),(3999,-.02,False),(4500,-.009,False),(4500,-.01,False),(4500,-.01001,True),(None,-.02,False)])
def test_trigger_counts_companies_not_index_points(count, ret, want):
    state = MarketTrigger().evaluate(3000, ret, DAY, declining_count=count)
    assert state.triggered is want
    assert state.declining_count == count


def test_actual_breadth_signal_trades_with_index_below_4000_and_matches_recommendation():
    frame = market_frame()
    strategy = FixedAssetStrategy('588000.SH')
    result = BacktestEngine(initial_cash=100000).run(frame, strategy)
    assert len(result.trades) == 1
    assert result.trades[0].signal_date == DAY
    assert result.trades[0].entry_date == date(2026,8,5)
    assert result.trades[0].exit_date == date(2026,8,6)
    rec = recommend(DAY, frame, strategy)
    assert rec.triggered and rec.selected.symbol == '588000.SH'
    assert rec.market.declining_count == 4200

@pytest.mark.parametrize('broken', ['missing_breadth','incomplete','wrong_scope','missing_today_index','wrong_return'])
def test_unusable_market_evidence_cannot_trigger(broken):
    frame = market_frame(closes=(4500, 4410, 4430, 4440))
    if broken == 'missing_breadth': frame = frame.drop(columns=['declining_count'])
    elif broken == 'incomplete': frame.loc[:,'breadth_complete'] = False
    elif broken == 'wrong_scope': frame.loc[:,'breadth_scope'] = 'candidate_pool'
    elif broken == 'missing_today_index': frame = frame[~((frame.symbol=='000001.SH') & (frame.date==pd.Timestamp(DAY)))]
    else: frame.loc[(frame.symbol=='000001.SH') & (frame.date==pd.Timestamp(DAY)), 'close'] = 4455
    rec = recommend(DAY, frame, FixedAssetStrategy())
    assert not rec.triggered
    assert rec.selected is None
    if broken != 'wrong_return': assert any('data quality' in w for w in rec.warnings)


def test_future_breadth_never_changes_past_signal():
    frame = market_frame()
    before = recommend(DAY, frame, FixedAssetStrategy()).to_dict()
    frame.loc[frame.date > pd.Timestamp(DAY), 'declining_count'] = 0
    assert recommend(DAY, frame, FixedAssetStrategy()).to_dict() == before
