from dataclasses import asdict
from pathlib import Path
from datetime import date
import pytest
from strategy.backtesting.engine import BacktestEngine
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.strategies.fixed import FixedAssetStrategy

ROOT=Path(__file__).resolve().parents[1]


def test_prepared_market_matches_normal_run_and_reuses_states(monkeypatch):
    frame=CsvMarketDataProvider(ROOT/'data/mvp_sample/market.csv').load()
    engine=BacktestEngine(100000,holding_period_days=3)
    strategy=FixedAssetStrategy()
    expected=engine.run(frame,strategy)
    prepared=engine.prepare_market(frame)
    def forbidden(*args):
        raise AssertionError('market states should be prepared once')
    monkeypatch.setattr(engine,'_market_state_with_warning',forbidden)
    for _ in range(2):
        assert asdict(engine.run_prepared(prepared,strategy))==asdict(expected)
    changed=BacktestEngine(100000,trigger_return_threshold=-.02)
    with pytest.raises(ValueError,match='trigger'):
        changed.run_prepared(prepared,strategy)


def test_preparation_keeps_validation_and_strategy_history_cutoff():
    frame=CsvMarketDataProvider(ROOT/'data/mvp_sample/market.csv').load()
    engine=BacktestEngine(100000)
    with pytest.raises(ValueError):
        engine.prepare_market(frame.drop(columns='open'))
    seen=[]
    class Observe:
        def select(self,as_of,market,universe):
            assert max(universe.date)<=as_of
            seen.append(as_of)
            universe.loc[:,'close']=999999  # 修改策略副本不能污染下一轮行情。
    prepared=engine.prepare_market(frame)
    before=engine.run_prepared(prepared,FixedAssetStrategy())
    engine.run_prepared(prepared,Observe(),start=date(2024,2,1))
    assert seen
    assert asdict(engine.run_prepared(prepared,FixedAssetStrategy()))==asdict(before)
