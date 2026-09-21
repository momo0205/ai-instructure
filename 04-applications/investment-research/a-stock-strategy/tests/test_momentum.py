from datetime import date
from pathlib import Path
import pandas as pd
import pytest
from strategy.domain import MarketState
from strategy.strategies.momentum import MomentumStrategy
from strategy import workbench

DAY = date(2024, 1, 3)
MARKET = MarketState(DAY, 3000, -.02, True)

def bars():
    return pd.DataFrame([dict(date=f'2024-01-0{d}', symbol=s, close=float(p)) for s, prices in [('A',[10,11,12,1]),('B',[10,11,11,100])] for d,p in enumerate(prices,1)])

def test_formula_and_future_isolation():
    strategy = MomentumStrategy(['B','A'], 2, 0)
    selected = strategy.select(DAY, MARKET, bars())
    assert selected.symbol == 'A'
    assert selected.score == pytest.approx(.2)
    assert selected.features['qlib_roc'] == pytest.approx(10/12)
    assert strategy.select(DAY, MARKET, bars().iloc[::-1]) == selected
    assert strategy.select(DAY, MarketState(DAY,3000,-.02,False),bars()) is None
    assert MomentumStrategy(['A'],2,.3).select(DAY,MARKET,bars()) is None

@pytest.mark.parametrize('bad',[0, -1, float('nan'),float('inf')])
def test_invalid_prices_rejected(bad):
    frame=bars();frame.loc[(frame.symbol=='A') & (frame.date=='2024-01-02'),'close']=bad
    assert MomentumStrategy(['A'],2).select(DAY,MARKET,frame) is None

def test_history_duplicates_flags_and_ties():
    strategy=MomentumStrategy(['A'],2)
    frame=bars()
    assert strategy.select(DAY,MARKET,frame[frame.date!='2024-01-03']) is None
    assert strategy.select(DAY,MARKET,pd.concat([frame,frame.iloc[:1]])) is None
    frame['is_suspended']=frame.symbol=='A'
    assert strategy.select(DAY,MARKET,frame) is None
    frame=bars();frame.loc[(frame.symbol=='B') & (frame.date=='2024-01-03'),'close']=12
    assert MomentumStrategy(['B','A'],2).select(DAY,MARKET,frame).symbol=='A'

@pytest.mark.parametrize('window',[True,0,1.5,253])
def test_invalid_window(window):
    with pytest.raises(ValueError): MomentumStrategy(['A'],window)

def test_workbench_registration_and_provenance(tmp_path):
    result=workbench.execute(Path(__file__).resolve().parents[1],{'strategy_id':'price_momentum','parameters':{'lookback':2,'minimum_momentum':-1}},tmp_path)
    assert result['equity'] and result['trades']
    assert result['metadata']['strategy_provenance']['reference_version']=='v0.9.7'
    assert result['request']['parameters']['lookback']==2
