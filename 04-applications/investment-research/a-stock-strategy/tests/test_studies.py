"""选参只能读取前段收益；后段必须在选择固定之后运行。"""
import json
from pathlib import Path
import time
import pytest
from strategy.application.studies import StudyManager, choose_candidate
from strategy.application.jobs import JobManager

ROOT = Path(__file__).resolve().parents[1]


def wait(getter, key):
    for _ in range(500):
        result = getter(key)
        if result['status'] not in ('queued','running','selecting','validating'):
            return result
        time.sleep(.02)
    raise AssertionError(result)


def test_selection_excludes_no_trade_and_ties_choose_shorter():
    rows=[{'holding_period_days':n,'status':'succeeded','metrics':{'cumulative_return':r,'trade_count':t}}
          for n,r,t in [(5,.1,2),(3,.1,2),(1,.9,0)]]
    assert choose_candidate(rows)==3
    assert choose_candidate([rows[-1]]) is None
    with pytest.raises(ValueError): choose_candidate(rows+[{'status':'failed'}])


def test_real_group_uses_same_snapshot_and_validates_only_locked_winner(tmp_path):
    jobs=JobManager(ROOT,tmp_path)
    studies=StudyManager(jobs)
    try:
        base=wait(jobs.get,jobs.submit({})['id'])
        batch=studies.submit({'base_job_id':base['id'],'holding_periods':[1,3,5],'validation_start':'2024-03-01'})
        done=wait(studies.get,batch['id'])
        assert done['status']=='completed',done
        assert len(done['training'])==3 and done['validation']['holding_period_days']==done['selected_holding_period_days']
        assert done['selection_end'] < done['validation_start']
        contexts=[]; hashes=[]
        for member in [*done['training'],done['validation']]:
            job=jobs.get(member['job_id']);metadata=job['result']['metadata']
            hashes.append({k:v for k,v in metadata['hashes'].items() if k!='request.json'})
            contexts.append(metadata['study'])
            assert job['request']['effectiveness'] is False
        assert all(h==hashes[0] for h in hashes)
        assert [c['phase'] for c in contexts]==['selection']*3+['validation']
        assert contexts[-1]['selected_holding_period_days']==done['selected_holding_period_days']
        assert len(jobs.list())==5
        with pytest.raises(ValueError): studies.submit({'base_job_id':base['id'],'holding_periods':[1,1],'validation_start':'2024-03-01'})
    finally:
        studies.close();jobs.close()
    reopened=JobManager(ROOT,tmp_path);history=StudyManager(reopened)
    try: assert history.get(batch['id'])['status']=='completed'
    finally: history.close();reopened.close()


def test_invalid_split_creates_no_member_jobs(tmp_path):
    jobs=JobManager(ROOT,tmp_path);studies=StudyManager(jobs)
    try:
        base=wait(jobs.get,jobs.submit({})['id'])
        for boundary in ('2024-01-02','2024-05-06','2025-01-01'):
            with pytest.raises(ValueError): studies.submit({'base_job_id':base['id'],'holding_periods':[1,3],'validation_start':boundary})
        assert len(jobs.list())==1
    finally: studies.close();jobs.close()

def test_failed_member_registration_cancels_child_and_keeps_coordinator_alive(tmp_path, monkeypatch):
    jobs=JobManager(ROOT,tmp_path);studies=StudyManager(jobs)
    try:
        base=wait(jobs.get,jobs.submit({})['id'])
        children={}
        def submit(request, root, context):
            key='c'*32
            children[key]={'id':key,'status':'running','request':request}
            return children[key]
        monkeypatch.setattr(jobs,'submit_frozen',submit)
        monkeypatch.setattr(jobs,'cancel',lambda key: children[key].update(status='cancelled') or children[key])
        original_save=studies._save
        def fail_member_write(record):
            if record.get('training'): raise OSError('disk failed')
            original_save(record)
        monkeypatch.setattr(studies,'_save',fail_member_write)
        batch=studies.submit({'base_job_id':base['id'],'holding_periods':[1,3],'validation_start':'2024-03-01'})
        done=wait(studies.get,batch['id'])
        assert done['status']=='failed'
        assert all(c['status']=='cancelled' for c in children.values())
        assert studies._thread.is_alive()
    finally: studies.close();jobs.close()


def test_corrupt_study_does_not_block_startup(tmp_path):
    from types import SimpleNamespace
    folder=tmp_path/'studies'/('d'*32);folder.mkdir(parents=True)
    (folder/'state.json').write_text('{invalid')
    studies=StudyManager(SimpleNamespace(state_dir=tmp_path))
    try:
        assert studies.list()['items'][0]['status']=='failed'
    finally: studies.close()

def test_no_trade_group_never_runs_validation(tmp_path):
    jobs=JobManager(ROOT,tmp_path);studies=StudyManager(jobs)
    try:
        base=wait(jobs.get,jobs.submit({'min_declining_count':100000})['id'])
        batch=studies.submit({'base_job_id':base['id'],'holding_periods':[1,3],'validation_start':'2024-03-01'})
        done=wait(studies.get,batch['id'])
        assert done['status']=='no_candidate'
        assert done['validation'] is None and len(jobs.list())==3
    finally: studies.close();jobs.close()


def test_cancelled_group_never_launches_validation(tmp_path, monkeypatch):
    jobs=JobManager(ROOT,tmp_path);studies=StudyManager(jobs)
    try:
        base=wait(jobs.get,jobs.submit({})['id']);children={};get=jobs.get
        def submit(request,root,context):
            key=str(len(children)+1)*32
            children[key]={'id':key,'status':'running','request':request}
            return children[key]
        monkeypatch.setattr(jobs,'submit_frozen',submit)
        monkeypatch.setattr(jobs,'get',lambda key:children[key] if key in children else get(key))
        monkeypatch.setattr(jobs,'cancel',lambda key:children[key].update(status='cancelled') or children[key])
        batch=studies.submit({'base_job_id':base['id'],'holding_periods':[1,3],'validation_start':'2024-03-01'})
        for _ in range(100):
            if len(children)==2:break
            time.sleep(.02)
        cancelled=studies.cancel(batch['id'])
        assert cancelled['status']=='cancelled' and cancelled['validation'] is None
        assert all(row['status']=='cancelled' for row in children.values())
        assert all(row['status']=='cancelled' for row in cancelled['training'])
    finally: studies.close();jobs.close()

def test_momentum_grid_locks_full_configuration(tmp_path):
    jobs=JobManager(ROOT,tmp_path);studies=StudyManager(jobs)
    try:
        base=wait(jobs.get,jobs.submit({'strategy_id':'price_momentum','parameters':{'lookback':2,'minimum_momentum':-1}})['id'])
        batch=studies.submit({'base_job_id':base['id'],'holding_periods':[1,3], 'lookbacks':[2,5],'validation_start':'2024-03-01'})
        done=wait(studies.get,batch['id'])
        assert done['status']=='completed', done
        assert {(m['holding_period_days'],m['lookback']) for m in done['training']}=={(1,2),(1,5),(3,2),(3,5)}
        winner=done['selected_candidate']
        validation=jobs.get(done['validation']['job_id'])
        assert validation['request']['holding_period_days']==winner['holding_period_days']
        assert validation['request']['parameters']['lookback']==winner['lookback']
        assert validation['result']['metadata']['study']['selected_candidate']==winner
        assert len(jobs.list())==6
        for member in done['training']:
            assert jobs.get(member['job_id'])['request']['parameters']['lookback']==member['lookback']
        for bad in ([2,2],[True,3],[0,2],list(range(1,9))):
            holds=list(range(1,9)) if len(bad)==8 else [1,3]
            with pytest.raises(ValueError): studies.submit({'base_job_id':base['id'],'holding_periods':holds,'lookbacks':bad,'validation_start':'2024-03-01'})
    finally:studies.close();jobs.close()


def test_fixed_strategy_rejects_window_grid(tmp_path):
    jobs=JobManager(ROOT,tmp_path);studies=StudyManager(jobs)
    try:
        base=wait(jobs.get,jobs.submit({})['id'])
        with pytest.raises(ValueError):studies.submit({'base_job_id':base['id'],'holding_periods':[1,3],'lookbacks':[2,5],'validation_start':'2024-03-01'})
        assert len(jobs.list())==1
    finally:studies.close();jobs.close()

def test_grid_tie_is_independent_of_candidate_order():
    from strategy.application.studies import choose_configuration
    rows=[dict(holding_period_days=h,lookback=w,status='succeeded',metrics=dict(trade_count=1,cumulative_return=.1)) for h,w in [(3,5),(1,5),(1,2)]]
    assert choose_configuration(rows)==choose_configuration(rows[::-1])=={'holding_period_days':1,'lookback':2}
