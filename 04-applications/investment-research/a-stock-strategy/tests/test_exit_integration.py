"""退出规则贯穿请求、冻结结果、实验记录及不兼容研究入口。"""
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from strategy.application.requests import validate_request
from strategy.application.backtests import execute
from strategy.interfaces.web.server import dispatch
from strategy.validation import UserError

ROOT = Path(__file__).resolve().parents[1]
SMA = {'id':'close_below_sma','parameters':{'window':3,'max_holding_days':8}}


def test_default_and_explicit_exit_request():
    assert validate_request(ROOT,{})['exit_policy']=={'id':'fixed_holding','parameters':{}}
    assert validate_request(ROOT,{'exit_policy':SMA})['exit_policy']==SMA


def test_catalog_exposes_rule_contract():
    status, catalog=dispatch('GET','/api/exit-policies',None,ROOT,None)
    assert status==200
    rule=next(x for x in catalog if x['id']=='close_below_sma')
    assert {p['name'] for p in rule['parameters']}=={'window','max_holding_days'}
    assert not rule['supports_effectiveness'] and not rule['supports_studies']


@pytest.mark.parametrize('value',[{},[],{'id':'bad'}, {'id':'fixed_holding','parameters':{'window':5}},
    {'id':'close_below_sma','parameters':{'window':True}}, {'id':'close_below_sma','parameters':{'window':1}},
    {'id':'close_below_sma','parameters':{'window':2,'extra':1}}])
def test_invalid_exit_rejected(value):
    with pytest.raises(UserError): validate_request(ROOT,{'exit_policy':value})


def test_incompatible_random_controls_fail_explicitly():
    with pytest.raises(UserError,match='固定持有期'):
        validate_request(ROOT,{'exit_policy':SMA,'effectiveness':True})


def test_internal_controls_cannot_silently_replace_exit():
    from strategy.application.effectiveness import compare_effectiveness
    plan=SimpleNamespace(engine_options={'exit_policy':SMA})
    with pytest.raises(UserError,match='固定持有期'):
        compare_effectiveness(plan,'588000.SH',{})


def test_execution_freezes_policy_and_exit_evidence(tmp_path):
    result=execute(ROOT,{'exit_policy':SMA,'trigger_return_threshold':0,'min_declining_count':0},tmp_path)
    assert result['request']['exit_policy']==SMA
    assert result['metadata']['exit_policy']['id']==SMA['id']
    assert result['metadata']['exit_policy']['version']
    assert result['exit_decision_events']
    assert any(e['sma'] is not None for e in result['exit_decision_events'])
    assert json.loads((tmp_path/'snapshot'/'request.json').read_text())['exit_policy']==SMA
    assert json.loads((tmp_path/'result.json').read_text())==result
    from strategy.storage.mlflow_export import flatten
    assert dict(flatten(result['request']))['exit_policy.parameters.window']==3


def test_nonfixed_batch_rejected_before_snapshot_io(tmp_path):
    from strategy.application.studies import StudyManager
    jobs=SimpleNamespace(state_dir=tmp_path,get=lambda key:{'id':key,'status':'succeeded','request':{'exit_policy':SMA}})
    studies=StudyManager(jobs)
    try:
        with pytest.raises(UserError,match='固定持有期'):
            studies.submit({'base_job_id':'a'*32,'holding_periods':[1,3],'validation_start':'2024-03-01'})
        assert not studies.list()['items']
    finally: studies.close()


def test_mlflow_exports_rule_version_and_effective_parameters(tmp_path,monkeypatch):
    import sys
    from strategy.storage.mlflow_export import export
    folder=tmp_path/'runs'/'a';folder.mkdir(parents=True)
    result={'request':{'strategy_id':'fixed_asset','holding_period_days':1,'exit_policy':SMA},
            'metadata':{'exit_policy':dict(SMA,version='sma-test-v1'),'exit_indicators':{'sma':'v1'}}}
    (folder/'result.json').write_text(json.dumps(result))
    batches=[]
    client=SimpleNamespace(get_experiment_by_name=lambda name:SimpleNamespace(experiment_id='1'),
        search_runs=lambda *a,**k:[],create_run=lambda *a,**k:SimpleNamespace(info=SimpleNamespace(run_id='r')),
        log_batch=lambda *a,**k:batches.append(k),log_artifact=lambda *a:None,set_terminated=lambda *a,**k:None)
    monkeypatch.setitem(sys.modules,'mlflow',SimpleNamespace(MlflowClient=lambda **k:client))
    monkeypatch.setitem(sys.modules,'mlflow.entities',SimpleNamespace(Param=lambda k,v:(k,v),Metric=lambda *a:a))
    export(tmp_path,'a')
    parameters={k:json.loads(v) for k,v in batches[0]['params']}
    assert parameters['exit_policy_version']=='sma-test-v1'
    assert parameters['exit_policy.parameters.window']==3
    assert 'holding_period_days' not in parameters


def test_sma_warmup_reports_actual_prior_input(tmp_path):
    result=execute(ROOT,{'exit_policy':{'id':'close_below_sma','parameters':{'window':20,'max_holding_days':20}}},tmp_path)
    warmup=result['metadata']['exit_warmup']['588000.SH']
    assert warmup=={'required_prior_sessions':19,'available_prior_sessions':0,'ready_at_start':False}
    assert any('退出指标暖机不足' in w for w in result['warnings'])
