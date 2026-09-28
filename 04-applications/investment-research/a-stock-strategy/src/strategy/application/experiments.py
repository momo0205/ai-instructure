"""实验同步旁路：持久化投递状态，独立线程调用独立 MLflow 环境。"""
import json
import logging
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
from urllib.parse import urlsplit


def failed_state():
    return {'status': 'failed', 'code': 'EXPERIMENT_SYNC_FAILED',
            'message': '实验记录同步失败，回测结果已保留；请检查实验环境后重试。'}


class ExperimentManager:
    def __init__(self, state_dir, python=None, ui_url='http://127.0.0.1:5000', *, exporter=None):
        self.root = Path(state_dir).resolve()
        self.folder = self.root / 'experiments'
        self.folder.mkdir(parents=True, exist_ok=True)
        # 子进程 cwd 与服务启动目录不同，启动时就固定解释器绝对路径。
        # abspath 保留 venv 的 python 符号链接；resolve 会指向基础解释器而丢失依赖。
        self.python = os.path.abspath(os.path.expanduser(shutil.which(python) or python)) if python else None
        url = urlsplit(ui_url)
        if url.scheme != 'http' or url.hostname not in ('localhost', '127.0.0.1') or url.username or url.password:
            raise ValueError('实验页面仅支持本机 HTTP 地址')
        self.ui_url = ui_url if python else None
        self.exporter = exporter or self._export
        self._lock = threading.RLock()
        self._queue = queue.Queue()
        self._closed = False
        self._volatile = {}
        self._thread = threading.Thread(target=self._worker, name='experiment-sync', daemon=True)
        # 上次进程中断留下 pending；同一个 run 的检查点用于幂等恢复。
        if python:
            for path in self.folder.glob('*.json'):
                if re.fullmatch('[0-9a-f]{32}', path.stem) and self.view(path.stem)['status'] == 'pending':
                    self._queue.put(path.stem)
        self._thread.start()

    def config(self):
        return {'enabled': bool(self.python), 'ui_url': self.ui_url}

    def _path(self, key):
        if not re.fullmatch('[0-9a-f]{32}', key):
            raise ValueError('无效任务编号')
        return self.folder / f'{key}.json'

    def view(self, key):
        with self._lock:
            if not self.python:
                return {'status': 'disabled'}
            if key in self._volatile:
                return dict(self._volatile[key])
            path = self._path(key)
            if not path.exists():
                return {'status': 'not_recorded'}
            try:
                value = json.loads(path.read_text())
                if not isinstance(value, dict) or value.get('status') not in ('pending', 'synced', 'failed'):
                    raise ValueError('invalid experiment state')
                return value
            except (OSError, ValueError):
                logging.getLogger(__name__).exception('实验同步状态损坏：%s', key)
                self._volatile[key] = failed_state()
                return dict(self._volatile[key])

    def _save(self, key, value):
        path = self._path(key)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False))
        temporary.replace(path)

    def enqueue(self, job):
        with self._lock:
            if not self.python or self._closed:
                raise ValueError('实验同步未启用')
            if job['status'] != 'succeeded':
                raise ValueError('仅成功回测可同步实验记录')
            key = job['id']
            if self.view(key)['status'] in ('pending', 'synced'):
                return
            self._save(key, {'status': 'pending'})
            self._volatile.pop(key, None)
            self._queue.put(key)

    def _export(self, key):
        script = Path(__file__).resolve().parents[1] / 'storage' / 'mlflow_export.py'
        # 参数只由本机配置与已验证任务 ID 组成；不经过 shell，不向页面返回 stderr。
        subprocess.run([self.python, str(script), str(self.root), key],
                       check=True, timeout=60, capture_output=True, cwd=self.root)
        value = json.loads((self.root / 'runs' / key / 'mlflow-run.json').read_text())
        return {'run_id': value['run_id'], 'experiment_id': value['experiment_id']}

    def _worker(self):
        while True:
            key = self._queue.get()
            if key is None:
                return
            try:
                record = self.exporter(key)
                value = dict(record, status='synced')
            except Exception:
                logging.getLogger(__name__).exception('实验同步失败：%s', key)
                value = failed_state()
            with self._lock:
                try:
                    self._save(key, value)
                except OSError:
                    # 磁盘暂不可写时仍提供可重试状态，不能终止整个队列。
                    # 磁盘中旧 pending 继续承担服务重启后的恢复依据。
                    logging.getLogger(__name__).exception('实验同步状态保存失败：%s', key)
                    self._volatile[key] = failed_state()

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            # 未开始的同步保留 pending，下次启动继续；只等待当前子进程。
            while True:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._queue.put(None)
        self._thread.join()
