from datetime import date
import json
from pathlib import Path
import sys
import pandas as pd
import pytest
from strategy.validation import UserError
from strategy.application.progress import progress_scope, TaskCancelled
from strategy.adapters.qlib_factors import compute_factors, run_worker, validate_output
from strategy.strategies.qlib_momentum import QlibMomentumStrategy
from strategy.domain import MarketState


def test_missing_environment_is_clear(tmp_path, monkeypatch):
    monkeypatch.setenv('A_STOCK_QLIB_PYTHON', str(tmp_path/'missing'))
    with pytest.raises(UserError) as error:
        compute_factors(pd.DataFrame(), ['588000.SH'], 2, tmp_path)
    assert error.value.code == 'QLIB_UNAVAILABLE'


def test_worker_failure_timeout_and_cancel(tmp_path):
    script=tmp_path/'worker.py';script.write_text('import time; time.sleep(10)')
    with pytest.raises(UserError) as error:
        run_worker([sys.executable,str(script)],tmp_path,timeout=.05)
    assert error.value.code=='QLIB_FAILED'
    def cancel(**kwargs): raise TaskCancelled()
    with progress_scope(cancel), pytest.raises(TaskCancelled):
        run_worker([sys.executable,str(script)],tmp_path,timeout=1)
    script.write_text('raise RuntimeError("private text")')
    with pytest.raises(UserError) as error:
        run_worker([sys.executable,str(script)],tmp_path)
    assert 'private text' not in str(error.value)


def test_output_validation():
    payload={'version':'0.9.7','expression':'$close/Ref($close, 2)-1','rows':[
        {'date':'2024-01-03','symbol':'588000.SH','score':.2}]}
    rows=validate_output(payload,['588000.SH'],['2024-01-03'],2)
    assert len(rows)==1
    for bad in [dict(payload,version='unknown'),dict(payload,rows=payload['rows']*2),dict(payload,rows=[dict(payload['rows'][0],score=float('inf'))]),dict(payload,expression='future')]:
        with pytest.raises(UserError):validate_output(bad,['588000.SH'],['2024-01-03'],2)


def test_cached_signals_only_use_current_date_and_valid_window():
    frame=pd.DataFrame([{'date':f'2024-01-0{i}','symbol':symbol,'close':10+i} for i in range(1,5) for symbol in ['000001.SH','588000.SH']])
    strategy=QlibMomentumStrategy(['588000.SH'],2,0)
    strategy.scores={('2024-01-03','588000.SH'):.2,('2024-01-04','588000.SH'):999}
    strategy.prepared=True
    day=date(2024,1,3); market=MarketState(day,3000,-.02,True)
    assert strategy.select(day,market,frame).score==.2
    missing=frame[~((frame.symbol=='588000.SH')&(frame.date=='2024-01-02'))]
    assert strategy.select(day,market,missing) is None
    assert strategy.select(day,MarketState(day,3000,-.02,False),frame) is None

def test_prepare_hook_receives_no_future_and_persists_runtime(tmp_path, monkeypatch):
    from strategy.strategies.registry import get_strategy_definition
    from strategy import workbench
    definition=get_strategy_definition('qlib_momentum')
    seen={}
    def prepare(strategy,market,output):
        seen['end']=market.date.max().date().isoformat()
        strategy.factor_runtime={'backend':'test-only'}
        strategy.prepared=True
        return strategy
    monkeypatch.setattr(definition,'prepare',prepare)
    result=workbench.execute(Path(__file__).resolve().parents[1],{'strategy_id':'qlib_momentum','end':'2024-03-01'},tmp_path)
    assert seen['end']=='2024-03-01'
    assert result['metadata']['factor_runtime']=={'backend':'test-only'}

def test_unprepared_strategy_cannot_silently_return_zero_trades():
    strategy=QlibMomentumStrategy(['588000.SH'],2)
    with pytest.raises(UserError) as error:
        strategy.select(date(2024,1,3),MarketState(date(2024,1,3),3000,-.02,True),pd.DataFrame())
    assert error.value.code=='QLIB_FAILED'
