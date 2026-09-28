"""普通股票的可用性及工作台接入，不依赖本机未提交的真实行情。"""
import json
from pathlib import Path
import shutil

import pandas as pd
import pytest

from strategy import workbench
from strategy.instruments import describe

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def stock_project(tmp_path):
    folder=tmp_path/'data'/'managed_stock'
    shutil.copytree(ROOT/'data'/'mvp_sample',folder)
    market=pd.read_csv(folder/'market.csv')
    stock=market[market.symbol=='588000.SH'].assign(symbol='002015.SZ')
    pd.concat([market,stock]).to_csv(folder/'market.csv',index=False)
    (folder/'market_manifest.json').write_text(json.dumps({
        'source':'test','adjustment':'qfq','instruments':{
            '002015.SZ':{'symbol':'002015.SZ','name':'协鑫能科','kind':'stock'}},
        'warnings':['仅三只已验证 ETF 支持回测。旧目录说明。'],
    }))
    return tmp_path


def test_verified_mainboard_metadata_enables_approximate_backtest():
    item=describe('002015.SZ',{'name':'协鑫能科','kind':'stock'})
    assert item['backtest_supported']
    assert item['execution_mode']=='approximate'
    assert item['backtest_start']=='2022-07-01'


@pytest.mark.parametrize('symbol,meta',[
    ('002015.SH',{'name':'协鑫能科','kind':'stock'}),
    ('300750.SZ',{'name':'宁德时代','kind':'stock'}),
    ('688001.SH',{'name':'科创股票','kind':'stock'}),
    ('002015.SZ',{'name':'ST股票','kind':'stock'}),
    ('002015.SZ',{'name':'退市股票','kind':'stock'}),
    ('002015.SZ',{'name':'协鑫能科','kind':'unknown'}),
    ('002015.SZ',{}),
])
def test_unsupported_or_unverified_security_stays_disabled(symbol,meta):
    assert not describe(symbol,meta)['backtest_supported']


def test_stock_result_exposes_cost_policy_and_execution_evidence(stock_project):
    request={'dataset_id':'managed_stock','parameters':{'symbol':'002015.SZ'}}
    result=workbench.execute(stock_project,request,stock_project/'result')
    assert result['trades']
    assert result['metadata']['execution_mode']=='approximate'
    assert result['metadata']['instrument_types']=={'002015.SZ':'stock'}
    assert result['metadata']['trading_rules_version']
    assert result['metadata']['stamp_duty_rate'] is None
    assert any('未知' in w and '涨跌停' in w for w in result['warnings'])
    assert any('前复权' in w for w in result['warnings'])
    assert result['execution_events']
    for trade in result['trades']:
        assert trade['stamp_duty']>0 and trade['transfer_fee']>0
        assert trade['fees']==pytest.approx(trade['commission']+trade['stamp_duty']+trade['transfer_fee'])


def test_mixed_candidates_get_individual_fee_types(stock_project):
    result=workbench.execute(stock_project,{'dataset_id':'managed_stock',
        'strategy_id':'cross_sectional_rank','parameters':{'candidate_symbols':['002015.SZ','588000.SH']}},stock_project/'result')
    assert result['metadata']['instrument_types']=={'002015.SZ':'stock','588000.SH':'etf'}


def test_old_stock_range_rejected_before_engine(stock_project):
    folder=stock_project/'data'/'managed_stock'
    for name in ('market.csv','breadth.csv'):
        data=pd.read_csv(folder/name)
        data['date']=data.date.str.replace('2024','2020')
        data.to_csv(folder/name,index=False)
    with pytest.raises(ValueError,match='2022-07-01'):
        workbench.validate_request(stock_project,{'dataset_id':'managed_stock','parameters':{'symbol':'002015.SZ'}})


def test_insufficient_cash_has_fee_aware_budget_evidence(stock_project):
    result=workbench.execute(stock_project,{'dataset_id':'managed_stock','parameters':{'symbol':'002015.SZ'},'initial_cash':1},stock_project/'small')
    event=next(e for e in result['execution_events'] if e['reason']=='insufficient_cash')
    assert event['cash']==1
    assert event['minimum_quantity']==100
    assert event['required_cash']>event['price']*100
    assert result['diagnostics'][0]['code']=='INSUFFICIENT_CASH'
