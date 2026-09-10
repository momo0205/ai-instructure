"""SQLite 持久任务队列。单个工作线程串行执行，取消后丢弃计算结果。"""
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import queue
import shutil
import sqlite3
import threading
import uuid
from strategy.application.backtests import validate_request, execute


class JobManager:
    """管理本机单用户任务。重启时未完成任务标记 interrupted，成功记录保留。"""

    def __init__(self, root, state_dir):
        self.root = Path(root)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True,exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.state_dir/'jobs.sqlite3',check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT NOT NULL, request TEXT NOT NULL, created_at TEXT NOT NULL, error TEXT, result TEXT)')
        self._db.execute("UPDATE jobs SET status='interrupted', error='服务重启，任务未完成；请重新提交' WHERE status IN ('queued','running')")
        self._db.commit()
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
            self._db.execute('INSERT INTO jobs VALUES (?,?,?,?,NULL,NULL)',(identifier,'queued',json.dumps(normalized,allow_nan=False),datetime.now(timezone.utc).isoformat()))
            self._db.commit()
            job = self.get(identifier)
            self._queue.put(identifier)
        return job

    @staticmethod
    def _decode(row, detail=True):
        value = dict(row)
        value['request'] = json.loads(value['request'])
        if detail and value['result'] is not None:
            value['result'] = json.loads(value['result'])
        else:
            value.pop('result',None)
        return value

    def list(self):
        """按创建时间倒序读取历史摘要，避免列表传输完整净值。"""
        with self._lock:
            return [self._decode(row,False) for row in self._db.execute('SELECT id, status, request, created_at, error FROM jobs ORDER BY created_at DESC')]

    def get(self, identifier):
        """查询详情；未知任务抛出 KeyError，成功任务包含结果。"""
        with self._lock:
            row = self._db.execute('SELECT * FROM jobs WHERE id=?',(identifier,)).fetchone()
            if row is None:
                raise KeyError('job not found')
            return self._decode(row)

    def cancel(self, identifier):
        """取消排队或运行任务；已完成状态保持不变，运行计算不会写回成功状态。"""
        with self._lock:
            self.get(identifier)
            self._db.execute("UPDATE jobs SET status='cancelled' WHERE id=? AND status IN ('queued','running')",(identifier,))
            self._db.commit()
            return self.get(identifier)

    def _worker(self):
        while True:
            identifier = self._queue.get()
            if identifier is None:
                return
            with self._lock:
                changed = self._db.execute("UPDATE jobs SET status='running' WHERE id=? AND status='queued'",(identifier,)).rowcount
                self._db.commit()
                if not changed:
                    continue
                request = self.get(identifier)['request']
            try:
                result = execute(self.state_dir/'runs'/identifier/'input_project',request,self.state_dir/'runs'/identifier)
                encoded = json.dumps(result,allow_nan=False)
                status,error = 'succeeded',None
            except Exception:
                # 异常原文可能包含路径、令牌或数据，公开接口仅给出固定说明。
                encoded,status,error = None,'failed','回测执行失败；请检查数据完整性和参数后重新提交'
            with self._lock:
                self._db.execute("UPDATE jobs SET status=?, error=?, result=? WHERE id=? AND status='running'",(status,error,encoded,identifier))
                self._db.commit()

    def close(self):
        """停止接收新任务，排队任务标记中断，等待当前计算安全结束后关闭数据库。"""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._db.execute("UPDATE jobs SET status='interrupted',error='服务关闭，任务未开始' WHERE status='queued'")
            self._db.commit()
            self._queue.put(None)
        self._thread.join()
        with self._lock:
            self._db.close()
