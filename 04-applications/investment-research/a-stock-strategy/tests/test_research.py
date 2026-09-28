"""中文研究页只访问所属任务，名称备注由真实实验存储持久化。"""
from types import SimpleNamespace
import json
import pytest
from strategy.application.research import ResearchService, ResearchUnavailable
from strategy.storage.mlflow_research import query_runs, label_run

KEY = 'a'*32
RUN = 'b'*32


def manager(enabled=True):
    row = {'id': KEY, 'status': 'succeeded', 'request': {'strategy_id':'fixed_asset'}, 'created_at':'2024-01-01'}
    return SimpleNamespace(
        experiments=SimpleNamespace(python='python' if enabled else None, root='/tmp', view=lambda key:{'status':'synced','run_id':RUN}),
        list=lambda:[row], get=lambda key:row if key == KEY else None)


def test_listing_filters_foreign_runs_and_preserves_missing_metrics():
    service = ResearchService(manager())
    service._invoke = lambda action,payload: [
        {'job_id':KEY,'run_id':RUN,'name':'','notes':'','metrics':{'cumulative_return':0},'controls':{}},
        {'job_id':'other','run_id':'c'*32}]
    result = service.list()
    assert len(result['items']) == 1
    assert result['items'][0]['request']['strategy_id'] == 'fixed_asset'
    assert 'win_rate' not in result['items'][0]['metrics']
    assert ResearchService(manager(False)).list() == {'enabled':False,'items':[],'limit':200}


def test_annotation_validation_and_no_arbitrary_run_id():
    service = ResearchService(manager())
    calls = []
    service._invoke = lambda action,payload: calls.append((action,payload)) or payload['annotation']
    assert service.label(KEY,{'name':' 持有三天 ','notes':'测试备注'}) == {'name':'持有三天','notes':'测试备注'}
    assert calls[0][1]['run_id'] == RUN
    for payload in ([], {'name':''},{'name':'x'*121},{'name':'x','notes':1},{'name':'x','run_id':'evil'}):
        with pytest.raises(ValueError): service.label(KEY,payload)
    assert len(calls)==1


def test_subprocess_failure_is_sanitized(monkeypatch):
    import strategy.application.research as module
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('secret-token')))
    with pytest.raises(ResearchUnavailable) as info: ResearchService(manager()).list()
    assert 'secret' not in str(info.value)


class Client:
    def __init__(self):
        self.tags={'job_id':KEY}
        self.run=SimpleNamespace(info=SimpleNamespace(run_id=RUN,experiment_id='1',status='FINISHED'),
            data=SimpleNamespace(tags=self.tags,params={'data_version':'"hash"','strategy_version':'"v1"'},
                                 metrics={'strategy.cumulative_return':.1,'effectiveness.random.median_return':.02}))
    def get_experiment_by_name(self,name): return SimpleNamespace(experiment_id='1')
    def get_experiment(self,key): return SimpleNamespace(name='a-stock-workbench')
    def search_runs(self,*a,**k): return [self.run]
    def get_run(self,key): return self.run
    def set_tag(self,key,name,value): self.tags[name]=value


def test_mlflow_annotation_roundtrip_and_controls_are_not_fabricated():
    client=Client()
    label_run(client,KEY,RUN,{'name':'三日持有','notes':'对照一日'})
    row=query_runs(client)[0]
    assert row['name']=='三日持有' and row['notes']=='对照一日'
    assert row['data_version']=='hash'
    assert row['controls']['random_median_return']==.02
    assert row['controls']['buy_hold_return'] is None
    with pytest.raises(ValueError): label_run(client,'c'*32,RUN,{'name':'错误','notes':''})
