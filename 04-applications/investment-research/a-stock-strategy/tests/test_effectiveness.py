from strategy.application.effectiveness import schedule_indices, compare_effectiveness
import random


def test_schedule_preserves_count_holding_period_and_bounds():
    a=schedule_indices(485,3,37,random.Random(4))
    assert a==schedule_indices(485,3,37,random.Random(4))
    assert len(a)==37 and len(set(a))==37
    assert min(a)>=0 and max(a)+1+3<485
    assert all(y-x>=4 for x,y in zip(a,a[1:]))


def test_empty_strategy_keeps_buy_and_hold_but_skips_random(tmp_path):
    from pathlib import Path
    from strategy.application.backtests import execute
    root=Path(__file__).resolve().parents[1]
    result=execute(root,{'effectiveness':True,'min_declining_count':100000},tmp_path/'empty')['effectiveness']
    assert result['status']=='available'
    assert result['buy_and_hold']['metrics']['trade_count']==1
    assert result['random']['status']=='unavailable'
    assert result['random']['reason_code']=='NO_COMPLETED_TRADES'


def test_controls_reuse_execution_rules_and_are_reproducible(tmp_path):
    from pathlib import Path
    from strategy.application.backtests import execute
    import strategy.application.effectiveness as module
    from unittest.mock import patch
    original=module.compare_effectiveness
    def small(plan,symbol,observed):
        return original(plan,symbol,observed,trials=3)
    root=Path(__file__).resolve().parents[1]
    request={'dataset_id':'mvp_sample','effectiveness':True,'holding_period_days':3}
    with patch.object(module,'compare_effectiveness',small):
        a=execute(root,request,tmp_path/'a')['effectiveness']
        b=execute(root,request,tmp_path/'b')['effectiveness']
    assert a==b and a['status']=='available'
    assert len(a['random']['samples'])==3
    assert 0<=a['random']['strategy_percentile']<=100
    assert all(len(s['signal_dates'])==a['target_trade_count'] for s in a['random']['samples'])
    assert a['buy_and_hold']['trades'][0]['fees']>0
    assert a['buy_and_hold']['trades'][0]['quantity']%100==0


def test_effectiveness_requires_boolean_and_fixed_strategy():
    from pathlib import Path
    import pytest
    from strategy.application.requests import validate_request
    root=Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError,match='effectiveness'):
        validate_request(root,{'effectiveness':'false'})
    with pytest.raises(ValueError,match='固定标的'):
        validate_request(root,{'effectiveness':True,'strategy_id':'cross_sectional_rank'})
