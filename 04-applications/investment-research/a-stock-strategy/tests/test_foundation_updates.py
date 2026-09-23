"""基础更新任务必须能跨请求观察，且凭据不能落盘或回显。"""
import json
import time
import pytest
from strategy.application import foundation_updates as module
from strategy.interfaces.web.server import dispatch


def terminal(manager):
    for _ in range(200):
        row=manager.list()[0]
        if row['status'] not in ('queued','running'): return row
        time.sleep(.01)
    raise AssertionError('task did not finish')


def test_update_keeps_credentials_out_of_history(tmp_path):
    seen=[]
    def update(root, identifier, start, end, *, token, progress):
        seen.append(token)
        progress(dict(stage='breadth',message='下载广度'))
        return 'foundation_'+identifier
    manager=module.FoundationUpdateManager(tmp_path,tmp_path/'state',updater=update)
    try:
        task=manager.submit(dict(start='2026-09-01',end='2026-09-21',token='test-private-token'))
        assert 'token' not in task['request']
        row=terminal(manager)
        assert row['status']=='succeeded'
        assert row['dataset_id'].startswith('foundation_')
        assert seen==['test-private-token']
        assert 'test-private-token' not in json.dumps(manager.list())
    finally: manager.close()
    assert b'test-private-token' not in (tmp_path/'state'/'foundations.sqlite3').read_bytes()


def test_provider_error_redacts_secret(tmp_path):
    def update(*args,token,**kwargs): raise ValueError('permission denied '+token)
    manager=module.FoundationUpdateManager(tmp_path,tmp_path/'state',updater=update)
    try:
        manager.submit(dict(start='2026-09-01',end='2026-09-21',token='test-private-token'))
        row=terminal(manager)
        assert row['status']=='failed'
        assert 'test-private-token' not in json.dumps(row)
        assert 'permission denied' in row['error']
    finally: manager.close()


def test_validation_and_routes(tmp_path,monkeypatch):
    monkeypatch.delenv('TUSHARE_TOKEN',raising=False)
    manager=module.FoundationUpdateManager(tmp_path,tmp_path/'state',updater=lambda *a,**k:'foundation_ok')
    try:
        with pytest.raises(ValueError,match='Tushare'): manager.submit(dict(start='2026-09-01',end='2026-09-21'))
        for request in [dict(start='2026-09-21',end='2026-09-01'),dict(start='2026-09-01',end='2999-01-01'),dict(start='bad',end='2026-09-21')]:
            with pytest.raises(ValueError): manager.submit(dict(request,token='x'))
        status,row=dispatch('POST','/api/foundation-updates',dict(start='2026-09-01',end='2026-09-21',token='x'),tmp_path,None,foundations=manager)
        assert status==202
        terminal(manager)
        status,rows=dispatch('GET','/api/foundation-updates',None,tmp_path,None,foundations=manager)
        assert status==200 and len(rows)==1
    finally: manager.close()


def test_catalog_reads_task_state_before_listing_published_versions(tmp_path,monkeypatch):
    from strategy.application.data_management import DataManagementService
    calls=[]
    class Tasks:
        def list(self): calls.append('tasks');return []
    def catalog(self): calls.append('catalog');return {}
    monkeypatch.setattr(DataManagementService,'catalog',catalog)
    status,_=dispatch('GET','/api/data-management',None,tmp_path,None,foundations=Tasks())
    assert status==200
    assert calls==['tasks','catalog']
