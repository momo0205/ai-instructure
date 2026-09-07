import time
from pathlib import Path
from strategy.jobs import JobManager
ROOT = Path(__file__).resolve().parents[1]

def wait(manager, identifier):
    for _ in range(200):
        job = manager.get(identifier)
        if job['status'] not in ('queued','running'):
            return job
        time.sleep(.02)
    raise AssertionError('job timed out')

def test_success_history_and_restart(tmp_path):
    manager = JobManager(ROOT,tmp_path)
    job = manager.submit({'dataset_id':'mvp_sample'})
    done = wait(manager,job['id'])
    assert done['status']=='succeeded' and done['result']['equity']
    manager.close()
    reopened = JobManager(ROOT,tmp_path)
    assert reopened.get(job['id'])['result']==done['result']
    assert reopened.list()[0]['id']==job['id']
    reopened.close()

def test_failure_is_sanitized(tmp_path,monkeypatch):
    import strategy.jobs as jobs
    def fail(*args):
        raise RuntimeError('/secret/path token=abc')
    monkeypatch.setattr(jobs,'execute',fail)
    manager = JobManager(ROOT,tmp_path)
    job = wait(manager,manager.submit({'dataset_id':'mvp_sample'})['id'])
    assert job['status']=='failed' and '/secret' not in job['error'] and 'abc' not in job['error']
    manager.close()

def test_cancel_cannot_be_overwritten(tmp_path,monkeypatch):
    import threading
    import strategy.jobs as jobs
    entered,release = threading.Event(),threading.Event()
    def slow(*args):
        entered.set()
        release.wait(3)
        return {'ok':True}
    monkeypatch.setattr(jobs,'execute',slow)
    manager = JobManager(ROOT,tmp_path)
    job=manager.submit({'dataset_id':'mvp_sample'})
    assert entered.wait(2)
    assert manager.cancel(job['id'])['status']=='cancelled'
    release.set()
    manager.close()
    reopened=JobManager(ROOT,tmp_path)
    assert reopened.get(job['id'])['status']=='cancelled'
    reopened.close()

def test_restart_marks_unfinished_interrupted(tmp_path):
    import sqlite3,json
    manager=JobManager(ROOT,tmp_path)
    manager.close()
    with sqlite3.connect(tmp_path/'jobs.sqlite3') as db:
        for status in ('queued','running'):
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,NULL,NULL)',(status,status,json.dumps({}),'2024-01-01'))
    manager=JobManager(ROOT,tmp_path)
    assert {job['status'] for job in manager.list()}=={'interrupted'}
    manager.close()

def test_submit_freezes_inputs_before_worker_executes(tmp_path,monkeypatch):
    import shutil,threading
    import strategy.jobs as jobs
    project=tmp_path/'project'
    shutil.copytree(ROOT/'data'/'mvp_sample',project/'data'/'mvp_sample')
    entered,release=threading.Event(),threading.Event()
    observed=[]
    def capture(root,request,output):
        entered.set()
        release.wait(3)
        observed.append((Path(root)/'data'/'mvp_sample'/'market.csv').read_text())
        return {'ok':True}
    monkeypatch.setattr(jobs,'execute',capture)
    manager=JobManager(project,tmp_path/'state')
    expected=(project/'data'/'mvp_sample'/'market.csv').read_text()
    job=manager.submit({})
    assert entered.wait(2)
    (project/'data'/'mvp_sample'/'market.csv').write_text('changed')
    release.set()
    assert wait(manager,job['id'])['status']=='succeeded'
    manager.close()
    assert observed==[expected]

def test_history_does_not_read_result_column(tmp_path):
    import sqlite3
    manager=JobManager(ROOT,tmp_path)
    # SQLite authorizer checks actual column access, including SELECT * expansion.
    def authorize(action, table, column, database, trigger):
        if action==sqlite3.SQLITE_READ and table=='jobs' and column=='result':
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    manager._db.set_authorizer(authorize)
    try:
        assert manager.list()==[]
    finally:
        manager._db.set_authorizer(None)
        manager.close()

def test_concurrent_data_change_rejected_before_enqueue(tmp_path, monkeypatch):
    import shutil
    import pytest
    import strategy.jobs as jobs
    project=tmp_path/'project'
    folder=project/'data'/'mvp_sample'
    shutil.copytree(ROOT/'data'/'mvp_sample',folder)
    copy=shutil.copyfile
    def changing_copy(source, target, *args, **kwargs):
        result=copy(source,target,*args,**kwargs)
        if Path(source)==folder/'market.csv':
            with Path(source).open('a') as stream:
                stream.write('\n')
        return result
    monkeypatch.setattr(jobs.shutil,'copyfile',changing_copy)
    manager=JobManager(project,tmp_path/'state')
    try:
        with pytest.raises(ValueError,match='更新'):
            manager.submit({})
        assert manager.list()==[]
    finally:
        manager.close()
