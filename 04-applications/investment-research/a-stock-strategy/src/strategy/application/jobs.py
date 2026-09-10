"""可替换存储的持久任务队列。单个工作线程串行执行，取消后丢弃计算结果。"""
from strategy.application.diagnostics import task_view, encode_error, exception_diagnostic
from datetime import datetime, timezone
from pathlib import Path
import json
import logging
import hashlib
import queue
import shutil
import threading
import uuid
from strategy.application.backtests import validate_request, execute
from strategy.storage.task_repository import TaskRepository, SQLiteTaskRepository


class JobManager:
    """管理本机单用户任务。重启时未完成任务标记 interrupted，成功记录保留。"""

    def __init__(self, root, state_dir, *, task_repository: TaskRepository | None = None):
        self.root = Path(root)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True,exist_ok=True)
        self._lock = threading.RLock()
        self.task_repository = task_repository if task_repository is not None else SQLiteTaskRepository(self.state_dir/'jobs.sqlite3')
        self.task_repository.interrupt(('queued', 'running'), '服务重启，任务未完成；请重新提交')
        self._queue = queue.Queue()
        self._closed = False
        self._thread = threading.Thread(target=self._worker,name='backtest-worker',daemon=True)
        self._thread.start()

    def submit(self, request):
        """先验证再落库；请求和任务目录彼此隔离，不接受调用方路径。"""
        normalized = validate_request(self.root,request)
        identifier = uuid.uuid4().hex
        with self._lock:
            if self._closed:
                raise RuntimeError('job manager closed')
            # 提交时即冻结输入；排队期间修改项目行情不会改变本次任务。
            frozen_root = self.state_dir/'runs'/identifier/'input_project'
            dataset = normalized['dataset_id']
            frozen_data = frozen_root/'data'/dataset
            frozen_data.mkdir(parents=True)
            names = ('market.csv','breadth.csv','manifest.json','market_manifest.json')
            def input_hashes(folder):
                return {name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
                        for name in names if (folder/name).is_file()}
            live_data = self.root/'data'/dataset
            before = input_hashes(live_data)
            for name in ('market.csv','breadth.csv','manifest.json','market_manifest.json'):
                source = self.root/'data'/dataset/name
                if source.is_file():
                    shutil.copyfile(source,frozen_data/name)
            # 兼容尚无内容哈希的历史清单：复制前后和副本必须完全一致。
            if before != input_hashes(live_data) or before != input_hashes(frozen_data):
                raise ValueError('数据在提交过程中更新，请稍后重试')
            if (self.root/'configs').is_dir():
                shutil.copytree(self.root/'configs',frozen_root/'configs')
            package = Path(__file__).parents[1]
            for source in package.rglob('*.py'):
                target = frozen_root/'src'/'strategy'/source.relative_to(package)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
            # 再验证冻结副本，避免验证原文件后复制到不完整的一组文件。
            validate_request(frozen_root,normalized)
            self.task_repository.create(identifier, normalized, datetime.now(timezone.utc).isoformat())
            job = self.get(identifier)
            self._queue.put(identifier)
        return job

    def list(self):
        """按创建时间倒序读取历史摘要，避免列表传输完整净值。"""
        with self._lock:
            return [task_view(row, 'backtest') for row in self.task_repository.list()]

    def get(self, identifier):
        """查询详情；未知任务抛出 KeyError，成功任务包含结果。"""
        with self._lock:
            return task_view(self.task_repository.get(identifier), 'backtest')

    def cancel(self, identifier):
        """取消排队或运行任务；已完成状态保持不变，运行计算不会写回成功状态。"""
        with self._lock:
            self.get(identifier)
            self.task_repository.transition(identifier, ('queued', 'running'), 'cancelled')
            return self.get(identifier)

    def _worker(self):
        while True:
            identifier = self._queue.get()
            if identifier is None:
                return
            with self._lock:
                changed = self.task_repository.transition(identifier, ('queued',), 'running')
                if not changed:
                    continue
                request = self.get(identifier)['request']
            try:
                result = execute(self.state_dir/'runs'/identifier/'input_project',request,self.state_dir/'runs'/identifier)
                json.dumps(result,allow_nan=False)
                status,error = 'succeeded',None
            except Exception as exception:
                logging.getLogger(__name__).exception('回测任务 %s 失败', identifier)
                # 异常原文可能包含路径、令牌或数据，公开接口仅给出固定说明。
                result,status,error = None,'failed',encode_error(exception_diagnostic(exception, 'backtest'))
            with self._lock:
                self.task_repository.transition(identifier, ('running',), status, error=error, result=result)

    def close(self):
        """停止接收新任务，排队任务标记中断，等待当前计算安全结束后关闭数据库。"""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self.task_repository.interrupt(('queued',), '服务关闭，任务未开始')
            self._queue.put(None)
        self._thread.join()
        with self._lock:
            self.task_repository.close()
