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
from time import monotonic
from strategy.application.progress import progress_scope, TaskCancelled
import uuid
from strategy.application.backtests import validate_request, execute
from strategy.storage.task_repository import TaskRepository, SQLiteTaskRepository
from strategy.application.experiments import ExperimentManager


class JobManager:
    """管理本机单用户任务。重启时未完成任务标记 interrupted，成功记录保留。"""

    def __init__(self, root, state_dir, *, task_repository: TaskRepository | None = None,
                 experiment_python=None, experiment_ui_url='http://127.0.0.1:5000'):
        self.root = Path(root)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True,exist_ok=True)
        self.experiments = ExperimentManager(self.state_dir, experiment_python, experiment_ui_url)
        self._lock = threading.RLock()
        self.task_repository = task_repository if task_repository is not None else SQLiteTaskRepository(self.state_dir/'jobs.sqlite3')
        self.task_repository.interrupt(('queued', 'running'), '服务重启，任务未完成；请重新提交')
        self._progress = {}
        self._started = {}
        self._queue = queue.Queue()
        self._closed = False
        self._thread = threading.Thread(target=self._worker,name='backtest-worker',daemon=True)
        self._thread.start()

    def submit(self, request):
        """先验证再落库；请求和任务目录彼此隔离，不接受调用方路径。"""
        if isinstance(request,dict) and 'snapshot_job_id' in request:
            import re
            key=request['snapshot_job_id']
            if not isinstance(key,str) or not re.fullmatch(r'[0-9a-f]{32}',key):
                raise ValueError('原始任务编号格式不合法')
            self.get(key)
            return self._submit(request,self.state_dir/'runs'/key/'input_project')
        return self._submit(request, self.root)

    def submit_frozen(self, request, source_root, study_context):
        """仅供内部研究编排调用；HTTP 请求不能指定 source_root。"""
        return self._submit(request, Path(source_root), study_context)

    def _submit(self, request, source_root, study_context=None, *, snapshot_input=False):
        normalized = validate_request(source_root,request)
        identifier = uuid.uuid4().hex
        if snapshot_input or 'snapshot_job_id' in normalized:
            normalized['snapshot_job_id'] = identifier
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
            live_data = source_root/'data'/dataset
            before = input_hashes(live_data)
            for name in ('market.csv','breadth.csv','manifest.json','market_manifest.json'):
                source = source_root/'data'/dataset/name
                if source.is_file():
                    shutil.copyfile(source,frozen_data/name)
            # 兼容尚无内容哈希的历史清单：复制前后和副本必须完全一致。
            if before != input_hashes(live_data) or before != input_hashes(frozen_data):
                raise ValueError('数据在提交过程中更新，请稍后重试')
            if (source_root/'configs').is_dir():
                shutil.copytree(source_root/'configs',frozen_root/'configs')
            package = source_root/'src'/'strategy' if study_context is not None else Path(__file__).parents[1]
            for source in package.rglob('*.py'):
                target = frozen_root/'src'/'strategy'/source.relative_to(package)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
            # 再验证冻结副本，避免验证原文件后复制到不完整的一组文件。
            validate_request(frozen_root,normalized)
            if study_context is not None:
                (frozen_root.parent/'study.json').write_text(json.dumps(study_context, allow_nan=False))
            self.task_repository.create(identifier, normalized, datetime.now(timezone.utc).isoformat())
            job = self.get(identifier)
            self._queue.put(identifier)
        return job

    def list(self):
        """按创建时间倒序读取历史摘要，避免列表传输完整净值。"""
        with self._lock:
            return [self._view(row) for row in self.task_repository.list()]

    def get(self, identifier):
        """查询详情；未知任务抛出 KeyError，成功任务包含结果。"""
        with self._lock:
            return self._view(self.task_repository.get(identifier))

    def _view(self, row):
        value = task_view(row, 'backtest')
        value['experiment'] = self.experiments.view(row['id'])
        if row['status'] == 'running' and row['id'] in self._progress:
            value['progress'] = dict(self._progress[row['id']],
                                     elapsed_seconds=round(monotonic()-self._started[row['id']],1))
        return value

    def sync_experiment(self, identifier):
        """显式补录历史成功任务，或重试失败同步；重复请求不重复建实验。"""
        with self._lock:
            self.experiments.enqueue(self.get(identifier))
            return self.get(identifier)

    def _update_progress(self, identifier, **event):
        with self._lock:
            if self.task_repository.get(identifier)['status'] != 'running':
                raise TaskCancelled()
            self._progress[identifier] = event

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
                self._started[identifier] = monotonic()
            try:
                with progress_scope(lambda **event: self._update_progress(identifier, **event)):
                    result = execute(self.state_dir/'runs'/identifier/'input_project',request,self.state_dir/'runs'/identifier)
                json.dumps(result,allow_nan=False)
                status,error = 'succeeded',None
            except TaskCancelled:
                result,status,error = None,'cancelled',None
            except Exception as exception:
                logging.getLogger(__name__).exception('回测任务 %s 失败', identifier)
                # 异常原文可能包含路径、令牌或数据，公开接口仅给出固定说明。
                result,status,error = None,'failed',encode_error(exception_diagnostic(exception, 'backtest'))
            with self._lock:
                changed = self.task_repository.transition(identifier, ('running',), status, error=error, result=result)
                if changed and status == 'succeeded' and self.experiments.config()['enabled']:
                    # 结果先落库，再异步同步；实验服务失败不能回滚已成功的回测。
                    try:
                        self.experiments.enqueue(self.get(identifier))
                    except Exception:
                        logging.getLogger(__name__).exception('实验同步入队失败：%s', identifier)
                self._progress.pop(identifier,None)
                self._started.pop(identifier,None)

    def close(self):
        """停止接收新任务，排队任务标记中断，等待当前计算安全结束后关闭数据库。"""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self.task_repository.interrupt(('queued',), '服务关闭，任务未开始')
            self._queue.put(None)
        self._thread.join()
        self.experiments.close()
        with self._lock:
            self.task_repository.close()
