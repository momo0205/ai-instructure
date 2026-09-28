"""市场基础数据任务：凭据只驻留队列内存，持久化记录仅保留日期和结果。"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from uuid import uuid4
import os
import queue
import threading
from strategy.storage.task_repository import SQLiteTaskRepository
from strategy.application.diagnostics import diagnostic, encode_error, task_view
from strategy.validation import UserError


class FoundationUpdateManager:
    def __init__(self, root, state_dir, *, updater=None):
        self.root = Path(root)
        self._uses_plan = updater is None
        if updater is None:
            from strategy.application.foundation_planning import update_missing
            updater = update_missing
        self.updater = updater
        self.repository = SQLiteTaskRepository(Path(state_dir)/'foundations.sqlite3', 'downloads')
        self.repository.interrupt(('queued','running'), '服务重启，请重新提交基础更新')
        self._lock = threading.RLock()
        self._queue = queue.Queue()
        self._progress = {}
        self._closed = False
        self._thread = threading.Thread(target=self._worker, name='foundation-update-worker', daemon=True)
        self._thread.start()

    def list(self):
        with self._lock:
            return [dict(task_view(row,'download'),progress=self._progress.get(row['id'])) for row in self.repository.list()]

    def submit(self, request):
        if not isinstance(request,dict) or set(request)-{'start','end','token'} or not {'start','end'} <= set(request):
            raise UserError('INVALID_REQUEST','基础更新需要 start、end，可选临时 token')
        try:
            start,end=(date.fromisoformat(request[k]) for k in ('start','end'))
            if any(d.isoformat()!=request[k] for d,k in ((start,'start'),(end,'end'))): raise ValueError
        except (ValueError,TypeError):
            raise UserError('INVALID_REQUEST','日期格式应为 YYYY-MM-DD') from None
        # 今日可能只有盘中截面；只发布已结束的历史日期。
        if not start<=end<datetime.now(ZoneInfo('Asia/Shanghai')).date():
            raise UserError('INVALID_REQUEST','开始日不能晚于结束日，结束日须早于北京时间今天')
        if (end-start).days>1096:
            raise UserError('INVALID_REQUEST','单次基础更新最多三年，请分段准备')
        token=request.get('token') or os.environ.get('TUSHARE_TOKEN')
        needs_token = True
        if self._uses_plan:
            from strategy.market_data.coverage import CoverageIndex
            plan = CoverageIndex(self.root).plan(start.isoformat(),end.isoformat())
            if plan['conflicts']:
                raise UserError('DATA_VALIDATION_FAILED','请求区间存在数据冲突，请先核对来源')
            needs_token = bool(plan['breadth_missing'])
        if needs_token and (not isinstance(token,str) or not token.strip()):
            raise UserError('INVALID_REQUEST','请提供临时 Tushare token，或在启动服务前设置 TUSHARE_TOKEN')
        if token is not None and not isinstance(token,str): raise UserError('INVALID_REQUEST','Tushare token 格式不合法')
        if token and len(token)>512: raise UserError('INVALID_REQUEST','Tushare token 长度不合法')
        identifier=uuid4().hex
        with self._lock:
            if self._closed: raise UserError('INVALID_REQUEST','基础更新服务已关闭')
            # 不序列化原始 request：其中可能含用户凭据。
            self.repository.create(identifier,dict(start=start.isoformat(),end=end.isoformat()),datetime.now(timezone.utc).isoformat())
            self._queue.put((identifier,token.strip() if token else None))
            return self.repository.get(identifier)

    def _worker(self):
        while True:
            item=self._queue.get()
            if item is None: return
            identifier,token=item
            item=None
            with self._lock:
                if not self.repository.transition(identifier,('queued',),'running'):
                    token=None
                    continue
                request=self.repository.get(identifier)['request']
            def progress(value):
                with self._lock:
                    self._progress[identifier]=dict(value)
            output,error=None,None
            try:
                output=self.updater(self.root,identifier,request['start'],request['end'],token=token,progress=progress)
                status='succeeded'
            except Exception as exc:
                # 不记录供应商异常堆栈，避免第三方异常将请求凭据写入日志。
                message=(str(exc).replace(token,'[REDACTED]') if token else str(exc)) if isinstance(exc,ValueError) else '基础数据更新失败，请检查连接或数据源权限后重试'
                error=encode_error(diagnostic('DOWNLOAD_FAILED',message=message))
                status='failed'
            finally:
                token=None
            with self._lock:
                self.repository.transition(identifier,('running',),status,error=error,dataset_id=output)
                self._progress.pop(identifier,None)

    def close(self):
        with self._lock:
            if self._closed: return
            self._closed=True
            self.repository.interrupt(('queued',),'服务关闭，请重试')
            self._queue.put(None)
        self._thread.join()
        self.repository.close()
