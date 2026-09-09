"""下载任务队列与旧导入兼容门面；数据获取和版本发布交给独立模块。"""
from datetime import date, datetime, timezone
from pathlib import Path
import json
import logging
import queue
import sqlite3
import threading
from urllib.request import urlopen
from uuid import uuid4
from .market_download import download_market
from .instrument_catalog import VERIFIED_ETFS, validate_symbol, describe
from .market_provider import MarketDataProvider, TencentMarketDataProvider, CallableMarketDataProvider
from .dataset_repository import DatasetRepository, LocalDatasetRepository


def resolve_instrument(symbol):
    """兼容旧名称与 opener 注入；解析规则只由腾讯适配器实现。"""
    return TencentMarketDataProvider(opener=urlopen).resolve(symbol)


def instrument_catalog(root):
    return [dict(item, dataset_id=dataset['id'])
            for dataset in LocalDatasetRepository(root).list() for item in dataset['instruments']]


class DownloadManager:
    """独立单线程下载队列，SQLite 保存历史；失败可重新提交，重启不自动重试。"""
    def __init__(self, root, state_dir, downloader=None, resolver=None, *,
                 provider: MarketDataProvider | None = None, repository: DatasetRepository | None = None):
        self.root, self.state_dir = Path(root), Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if provider is not None and (downloader is not None or resolver is not None):
            raise ValueError('provider 与旧 downloader/resolver 注入不能同时指定')
        self.provider = provider if provider is not None else (
            CallableMarketDataProvider(downloader or download_market, resolver or resolve_instrument)
            if downloader is not None or resolver is not None else TencentMarketDataProvider())
        self.repository = repository if repository is not None else LocalDatasetRepository(self.root)
        self._lock, self._queue, self._closed = threading.RLock(), queue.Queue(), False
        self._db = sqlite3.connect(self.state_dir/'downloads.sqlite3', check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute('CREATE TABLE IF NOT EXISTS downloads (id TEXT PRIMARY KEY, status TEXT, request TEXT, created_at TEXT, error TEXT, dataset_id TEXT)')
        self._db.execute("UPDATE downloads SET status='interrupted',error='服务重启，请重试' WHERE status IN ('queued','running')")
        self._db.commit()
        self._thread = threading.Thread(target=self._worker, name='market-download-worker', daemon=True)
        self._thread.start()

    def list(self):
        with self._lock:
            return [dict(row, request=json.loads(row['request'])) for row in self._db.execute('SELECT * FROM downloads ORDER BY created_at DESC')]

    def submit(self, request):
        if not isinstance(request, dict) or set(request) != {'symbol','start','end'}:
            raise ValueError('新增代码需要 symbol、start、end')
        validate_symbol(request['symbol'])
        try:
            for key in ('start','end'):
                if date.fromisoformat(request[key]).isoformat() != request[key]:
                    raise ValueError
        except (ValueError, TypeError):
            raise ValueError('下载日期格式应为 YYYY-MM-DD') from None
        base = next((item for item in self.repository.list() if item['id']=='real'), None)
        if base is None:
            raise ValueError('需要先准备真实基线数据（data/real）；不允许与合成样例混合')
        if not base['start'] <= request['start'] <= request['end'] <= base['end']:
            raise ValueError(f"下载范围必须位于真实基线 {base['start']} 至 {base['end']}，以匹配指数和市场广度")
        identifier = uuid4().hex
        with self._lock:
            if self._closed:
                raise ValueError('下载服务已关闭')
            self._db.execute('INSERT INTO downloads VALUES (?,?,?,?,NULL,NULL)', (identifier,'queued',json.dumps(request),datetime.now(timezone.utc).isoformat()))
            self._db.commit()
            task = next(x for x in self.list() if x['id']==identifier)
            self._queue.put(identifier)
            return task

    def _publish(self, identifier, request):
        """任务只协调数据源与仓库，不包含供应商格式或文件合并规则。"""
        metadata = self.provider.resolve(request['symbol'])
        if metadata.get('symbol') != request['symbol']:
            raise ValueError('证券元数据代码不匹配')
        prepared = self.repository.prepare(identifier)
        self.provider.download(request['start'], request['end'], prepared.stage/'download',
                               symbols=[request['symbol']], adjustment=prepared.adjustment)
        return self.repository.publish(prepared, request, metadata)

    def _worker(self):
        while True:
            identifier = self._queue.get()
            if identifier is None:
                return
            with self._lock:
                if not self._db.execute("UPDATE downloads SET status='running' WHERE id=? AND status='queued'", (identifier,)).rowcount:
                    continue
                self._db.commit()
                request = next(x['request'] for x in self.list() if x['id']==identifier)
            dataset_id, error = None, None
            try:
                dataset_id = self._publish(identifier, request)
                status = 'succeeded'
            except Exception as exception:
                logging.getLogger(__name__).exception('下载任务 %s 失败', identifier)
                status = 'failed'
                error = str(exception) if isinstance(exception, ValueError) else '数据源请求或文件处理失败，请检查服务日志并重试'
            with self._lock:
                self._db.execute('UPDATE downloads SET status=?,error=?,dataset_id=? WHERE id=?', (status,error,dataset_id,identifier))
                self._db.commit()

    def close(self):
        """关闭时中断未开始任务，等待有限超时的在途网络请求结束。"""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._db.execute("UPDATE downloads SET status='interrupted',error='服务关闭，请重试' WHERE status='queued'")
            self._db.commit()
            self._queue.put(None)
        self._thread.join()
        self._db.close()
