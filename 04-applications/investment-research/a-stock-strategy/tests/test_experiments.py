"""实验同步是可重试的旁路，不能改变回测结果或阻塞计算线程。"""
import json
import threading
import time
from pathlib import Path

import pytest
from strategy.application.experiments import ExperimentManager


def wait(manager, key, status):
    for _ in range(300):
        value = manager.view(key)
        if value['status'] == status:
            return value
        time.sleep(.01)
    raise AssertionError(value)


def job():
    return {'id': 'a' * 32, 'status': 'succeeded', 'request': {}}


def test_disabled_and_non_success(tmp_path):
    manager = ExperimentManager(tmp_path)
    try:
        assert manager.view(job()['id'])['status'] == 'disabled'
        with pytest.raises(ValueError):
            manager.enqueue(job())
    finally:
        manager.close()


def test_relative_interpreter_fixed_before_subprocess_changes_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    interpreter = tmp_path / 'env' / 'python'
    interpreter.parent.mkdir()
    interpreter.write_text('#!/bin/sh\n')
    interpreter.chmod(0o755)
    manager = ExperimentManager(tmp_path/'state', python='env/python')
    try:
        assert manager.python == str(interpreter)
    finally:
        manager.close()


def test_failure_retry_and_deduplication(tmp_path):
    calls = []
    entered, release = threading.Event(), threading.Event()
    def export(key):
        calls.append(key)
        if len(calls) == 1:
            raise RuntimeError('token=private-secret')
        entered.set()
        assert release.wait(3)
        return {'run_id': 'b' * 32, 'experiment_id': '1'}
    manager = ExperimentManager(tmp_path, python='python', exporter=export)
    try:
        with pytest.raises(ValueError):
            manager.enqueue(job() | {'status': 'cancelled'})
        manager.enqueue(job())
        failed = wait(manager, job()['id'], 'failed')
        assert 'private-secret' not in json.dumps(failed)
        manager.enqueue(job())
        assert entered.wait(2)
        manager.enqueue(job())
        release.set()
        assert wait(manager, job()['id'], 'synced')['run_id'] == 'b' * 32
        manager.enqueue(job())
        assert len(calls) == 2
    finally:
        release.set()
        manager.close()
    reopened = ExperimentManager(tmp_path, python='python', exporter=export)
    try:
        assert reopened.view(job()['id'])['status'] == 'synced'
    finally:
        reopened.close()


def test_pending_recovered_after_restart(tmp_path):
    folder = tmp_path / 'experiments'
    folder.mkdir()
    (folder / (job()['id'] + '.json')).write_text('{"status":"pending"}')
    manager = ExperimentManager(tmp_path, python='python', exporter=lambda key: {'run_id': 'b'*32, 'experiment_id': '1'})
    try:
        wait(manager, job()['id'], 'synced')
    finally:
        manager.close()


def test_successful_job_exports_without_waiting_for_tracker(tmp_path):
    from strategy.application.jobs import JobManager
    entered, release = threading.Event(), threading.Event()
    manager = JobManager(Path(__file__).resolve().parents[1], tmp_path, experiment_python='python')
    def export(key):
        entered.set()
        assert release.wait(4)
        return {'run_id': 'b'*32, 'experiment_id': '1'}
    manager.experiments.exporter = export
    try:
        identifier = manager.submit({})['id']
        assert entered.wait(3)
        done = manager.get(identifier)
        assert done['status'] == 'succeeded' and done['result']['equity']
        assert done['experiment']['status'] == 'pending'
        release.set()
        wait(manager.experiments, identifier, 'synced')
    finally:
        release.set()
        manager.close()


def test_state_write_failure_does_not_kill_queue(tmp_path, monkeypatch):
    manager = ExperimentManager(tmp_path, python='python', exporter=lambda key: {'run_id': 'b'*32, 'experiment_id': '1'})
    save = manager._save
    def fail_completed(key, value):
        if value['status'] == 'synced':
            raise OSError('disk unavailable')
        return save(key, value)
    monkeypatch.setattr(manager, '_save', fail_completed)
    try:
        manager.enqueue(job())
        wait(manager, job()['id'], 'failed')
        monkeypatch.setattr(manager, '_save', save)
        manager.enqueue(job())
        wait(manager, job()['id'], 'synced')
        manager.enqueue(job() | {'id': 'c'*32})
        wait(manager, 'c'*32, 'synced')
    finally:
        manager.close()


def test_corrupt_sync_state_does_not_hide_backtest(tmp_path):
    folder = tmp_path / 'experiments'
    folder.mkdir()
    (folder / (job()['id'] + '.json')).write_text('{broken')
    manager = ExperimentManager(tmp_path, python='python', exporter=lambda key: {'run_id': 'b'*32, 'experiment_id': '1'})
    try:
        assert manager.view(job()['id'])['status'] == 'failed'
        manager.enqueue(job())
        wait(manager, job()['id'], 'synced')
    finally:
        manager.close()
