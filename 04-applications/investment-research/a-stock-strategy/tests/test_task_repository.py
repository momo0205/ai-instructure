"""A non-SQL store exercises the same worker lifecycle and real business execution."""
from copy import deepcopy
from pathlib import Path
import time


class MemoryTaskRepository:
    def __init__(self, output_field='result'):
        self.rows = {}
        self.output_field = output_field

    def create(self, identifier, request, created_at):
        self.rows[identifier] = dict(id=identifier, status='queued', request=deepcopy(request),
                                    created_at=created_at, error=None, **{self.output_field: None})

    def get(self, identifier):
        value = deepcopy(self.rows[identifier])
        if self.output_field == 'result' and value['result'] is None:
            value.pop('result')
        return value

    def list(self):
        rows = sorted((self.get(key) for key in self.rows), key=lambda row: row['created_at'], reverse=True)
        if self.output_field == 'result':
            for row in rows:
                row.pop('result', None)
        return rows

    def transition(self, identifier, expected, status, **changes):
        row = self.rows[identifier]
        if row['status'] not in expected:
            return False
        row.update(status=status, **deepcopy(changes))
        return True

    def interrupt(self, statuses, error):
        for identifier in self.rows:
            self.transition(identifier, statuses, 'interrupted', error=error)

    def close(self):
        pass


def test_real_job_with_memory_storage(tmp_path):
    from strategy.jobs import JobManager
    manager = JobManager(Path(__file__).resolve().parents[1], tmp_path, task_repository=MemoryTaskRepository())
    try:
        identifier = manager.submit({'dataset_id': 'mvp_sample'})['id']
        for _ in range(300):
            task = manager.get(identifier)
            if task['status'] not in ('queued', 'running'):
                break
            time.sleep(.02)
        assert task['status'] == 'succeeded', task
        assert task['result']['equity']
        assert not list(tmp_path.rglob('*.sqlite3'))
    finally:
        manager.close()


def test_sqlite_conditional_transition_preserves_cancelled_and_old_schema(tmp_path):
    import json
    import sqlite3
    from strategy.storage.task_repository import SQLiteTaskRepository
    for kind, field in [('jobs', 'result'), ('downloads', 'dataset_id')]:
        path = tmp_path / f'{kind}.sqlite3'
        with sqlite3.connect(path) as db:
            db.execute(f'CREATE TABLE {kind} (id TEXT PRIMARY KEY, status TEXT, request TEXT, created_at TEXT, error TEXT, {field} TEXT)')
            output = json.dumps({'equity': [1]}) if kind == 'jobs' else 'managed_old'
            db.execute(f'INSERT INTO {kind} VALUES (?,?,?,?,?,?)', ('old', 'succeeded', '{}', '2024', None, output))
        repository = SQLiteTaskRepository(path, kind)
        try:
            assert repository.get('old')[field] == ({'equity': [1]} if kind == 'jobs' else 'managed_old')
            repository.create('new', {'symbol': 'test'}, '2025')
            assert repository.transition('new', ('queued',), 'running')
            assert repository.transition('new', ('queued', 'running'), 'cancelled')
            assert not repository.transition('new', ('running',), 'succeeded', **{field: output})
            assert repository.get('new')['status'] == 'cancelled'
            repository.create('pending', {}, '2026')
            repository.interrupt(('queued',), 'closed')
            assert repository.get('pending')['status'] == 'interrupted'
            assert repository.list()[0]['id'] == 'pending'
        finally:
            repository.close()
