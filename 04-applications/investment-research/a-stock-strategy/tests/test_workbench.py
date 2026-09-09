from pathlib import Path
import json
import pytest
from strategy import workbench
from strategy.registry import catalog

ROOT = Path(__file__).resolve().parents[1]

def test_catalog_and_sample_execution(tmp_path):
    assert {x['id'] for x in catalog()} == {'fixed_asset', 'cross_sectional_rank'}
    ds = next(x for x in workbench.datasets(ROOT) if x['id'] == 'mvp_sample')
    result = workbench.execute(ROOT, {'dataset_id':'mvp_sample','start':'2024-02-01'}, tmp_path)
    assert result['equity'] and all(x['date'] >= '2024-02-01' for x in result['equity'])
    assert all(x['signal_date'] >= '2024-02-01' for x in result['trades'])
    assert ds['sample'] and result['metadata']['hashes']
    assert json.loads((tmp_path/'result.json').read_text()) == result
    assert (tmp_path/'snapshot'/'market.csv').is_file()

@pytest.mark.parametrize('change', [{'wat':1}, {'initial_cash':float('nan')}, {'holding_period_days':1.5}, {'holding_period_days':True}, {'start':'2024-02-30'}, {'start':'1999-01-01'}, {'parameters':{'symbol':'MISSING'}}, {'parameters':{'unknown':1}}, {'strategy_id':'cross_sectional_rank','parameters':{'momentum_window':1.5}}, {'commission_rate':-1}])
def test_strict_validation(change):
    with pytest.raises(ValueError):
        workbench.validate_request(ROOT, {'dataset_id':'mvp_sample'} | change)

def test_rank_warmup_warning(tmp_path):
    result = workbench.execute(ROOT, {'dataset_id':'mvp_sample', 'strategy_id':'cross_sectional_rank'},tmp_path)
    assert any('warmup' in w for w in result['warnings'])

def test_etf_cost_policy_and_real_metadata(tmp_path):
    result = workbench.execute(ROOT,{'dataset_id':'mvp_sample'},tmp_path)
    assert result['metadata']['stamp_duty_rate']==0
    assert result['metadata']['lot_size']==100

def test_defaults_match_real_strategy_configuration():
    request = workbench.validate_request(ROOT,{'strategy_id':'cross_sectional_rank'})
    assert request['trigger_return_threshold']==-.01
    assert request['parameters']['candidate_symbols']==['588000.SH','510300.SH','159915.SZ']
    assert request['parameters']['weights']==dict(momentum=0.,reversal=1.,volatility=-.25,volume=0.)

def test_missing_breadth_day_rejected(tmp_path):
    import shutil,pandas as pd
    folder=tmp_path/'data'/'mvp_sample'
    shutil.copytree(ROOT/'data'/'mvp_sample',folder)
    breadth=pd.read_csv(folder/'breadth.csv')
    breadth.iloc[1:].to_csv(folder/'breadth.csv',index=False)
    with pytest.raises(ValueError,match='breadth'):
        workbench.validate_request(tmp_path,{})

def test_unrelated_symbol_sessions_do_not_change_calendar(tmp_path):
    import shutil,pandas as pd
    original=workbench.execute(ROOT,{'start':'2024-02-01'},tmp_path/'original')
    folder=tmp_path/'data'/'mvp_sample'
    shutil.copytree(ROOT/'data'/'mvp_sample',folder)
    market=pd.read_csv(folder/'market.csv')
    extra=market.iloc[[0]].copy()
    extra['date']='2024-02-03'
    extra['symbol']='UNRELATED'
    pd.concat([market,extra]).sort_values('date').to_csv(folder/'market.csv',index=False)
    changed=workbench.execute(tmp_path,{'start':'2024-02-01'},tmp_path/'changed')
    assert changed['equity']==original['equity']
    assert changed['trades']==original['trades']

def test_market_manifest_overrides_static_config_provenance(tmp_path):
    """重新下载行情后，页面必须采用本次下载清单而不是旧 TOML。"""
    import shutil
    root = tmp_path/'project'
    shutil.copytree(ROOT/'data'/'mvp_sample',root/'data'/'mvp_sample')
    (root/'configs').mkdir()
    shutil.copy(ROOT/'configs'/'mvp.toml',root/'configs'/'mvp.toml')
    (root/'data'/'mvp_sample'/'market_manifest.json').write_text(json.dumps({
        'source':'fresh-market-source','adjustment':'qfq',
        'warnings':['fresh warning']}))
    dataset=workbench.datasets(root)[0]
    assert dataset['market_source']=='fresh-market-source'
    assert dataset['adjustment']=='qfq'
    assert 'fresh warning' in dataset['warnings']

@pytest.mark.parametrize('manifest,field,filename', [
    ('market_manifest.json','market_sha256','market.csv'),
    ('manifest.json','breadth_sha256','breadth.csv'),
])
def test_mismatched_manifest_rejected(tmp_path, manifest, field, filename):
    import shutil
    folder=tmp_path/'data'/'mvp_sample'
    shutil.copytree(ROOT/'data'/'mvp_sample',folder)
    (folder/manifest).write_text(json.dumps({field:'stale-hash'}))
    with pytest.raises(ValueError,match='hash'):
        workbench.validate_request(tmp_path,{})

def test_dataset_bounds_use_index_calendar(tmp_path):
    import shutil,pandas as pd
    folder=tmp_path/'data'/'mvp_sample'
    shutil.copytree(ROOT/'data'/'mvp_sample',folder)
    market=pd.read_csv(folder/'market.csv')
    expected=workbench.datasets(tmp_path)[0]
    extra=market.iloc[[0,0]].copy()
    extra['date']=['1999-01-01','2099-01-01']
    extra['symbol']='UNRELATED'
    pd.concat([market,extra]).sort_values('date').to_csv(folder/'market.csv',index=False)
    actual=workbench.datasets(tmp_path)[0]
    assert (actual['start'],actual['end'])==(expected['start'],expected['end'])

def test_registry_entry_controls_catalog_and_constructor(monkeypatch):
    import strategy.registry as registry
    monkeypatch.setattr(registry, '_REGISTRY', {})
    definition = registry.StrategyDefinition(
        id='test_strategy', name='Test', description='Test', version='test', parameters=[],
        constructor=lambda **kwargs: kwargs, symbol_selector=lambda p: [],
    )
    registry.register_strategy(definition)
    assert registry.catalog() == [dict(id='test_strategy', name='Test', description='Test', version='test', parameters=[])]
    assert registry.build_strategy('test_strategy', {'hello': 1}) == {'hello': 1}
