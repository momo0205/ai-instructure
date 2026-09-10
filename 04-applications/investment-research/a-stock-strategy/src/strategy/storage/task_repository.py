"""Task persistence contract and the compatible local SQLite implementation."""
import json
from pathlib import Path
import sqlite3
import threading
from typing import Protocol


class TaskRepository(Protocol):
    """Stores decoded task records; transitions must atomically check the old status.

    Job history excludes result payloads. Managers own and close their repository.
    """
    def create(self, identifier: str, request: dict, created_at: str) -> None: ...
    def get(self, identifier: str) -> dict: ...
    def list(self) -> list[dict]: ...
    def transition(self, identifier: str, expected: tuple[str, ...], status: str, **changes) -> bool: ...
    def interrupt(self, statuses: tuple[str, ...], error: str) -> None: ...
    def close(self) -> None: ...


class SQLiteTaskRepository:
    """Retains the existing jobs/downloads table layouts and JSON response shapes."""
    def __init__(self, path, kind='jobs'):
        if kind not in ('jobs', 'downloads'):
            raise ValueError('unknown task kind')
        self.kind = kind
        self.output_field = 'result' if kind == 'jobs' else 'dataset_id'
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        fields = ('id TEXT PRIMARY KEY, status TEXT NOT NULL, request TEXT NOT NULL, created_at TEXT NOT NULL, error TEXT, result TEXT'
                  if kind == 'jobs' else 'id TEXT PRIMARY KEY, status TEXT, request TEXT, created_at TEXT, error TEXT, dataset_id TEXT')
        self._db.execute(f'CREATE TABLE IF NOT EXISTS {kind} ({fields})')
        self._db.commit()

    def create(self, identifier, request, created_at):
        with self._lock, self._db:
            self._db.execute(f'INSERT INTO {self.kind} VALUES (?,?,?,?,NULL,NULL)',
                             (identifier, 'queued', json.dumps(request, allow_nan=False), created_at))

    def _decode(self, row):
        value = dict(row)
        value['request'] = json.loads(value['request'])
        if 'result' in value:
            if value['result'] is None:
                value.pop('result')
            else:
                value['result'] = json.loads(value['result'])
        return value

    def get(self, identifier):
        with self._lock:
            row = self._db.execute(f'SELECT * FROM {self.kind} WHERE id=?', (identifier,)).fetchone()
            if row is None:
                raise KeyError('job not found' if self.kind == 'jobs' else 'download not found')
            return self._decode(row)

    def list(self):
        columns = 'id, status, request, created_at, error' if self.kind == 'jobs' else '*'
        with self._lock:
            return [self._decode(row) for row in self._db.execute(
                f'SELECT {columns} FROM {self.kind} ORDER BY created_at DESC')]

    def transition(self, identifier, expected, status, **changes):
        if set(changes) - {'error', self.output_field}:
            raise ValueError('unknown task fields')
        if not expected:
            return False
        if 'result' in changes and changes['result'] is not None:
            changes['result'] = json.dumps(changes['result'], allow_nan=False)
        assignments = ', '.join(f'{field}=?' for field in changes)
        suffix = ', ' + assignments if assignments else ''
        placeholders = ','.join('?' for _ in expected)
        with self._lock, self._db:
            return bool(self._db.execute(
                f'UPDATE {self.kind} SET status=?{suffix} WHERE id=? AND status IN ({placeholders})',
                (status, *changes.values(), identifier, *expected)).rowcount)

    def interrupt(self, statuses, error):
        if not statuses:
            return
        placeholders = ','.join('?' for _ in statuses)
        with self._lock, self._db:
            self._db.execute(f"UPDATE {self.kind} SET status='interrupted',error=? WHERE status IN ({placeholders})",
                             (error, *statuses))

    def close(self):
        with self._lock:
            self._db.close()
