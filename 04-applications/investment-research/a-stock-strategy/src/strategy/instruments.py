"""证券目录及独立行情准备队列；已发布版本只读，回测不触发网络。

可下载不等于可回测。只有已验证的境内 ETF 使用当前交易费用模型，
股票与其他基金保留行情供研究，直到相应交易规则得到实现和验证。
"""
from datetime import date, datetime, timezone
from pathlib import Path
import hashlib
import json
import logging
import queue
import re
import shutil
import sqlite3
import threading
import tomllib
from urllib.request import Request, urlopen
from uuid import uuid4

import pandas as pd
from .market_download import download_market

VERIFIED_ETFS = {'588000.SH':'科创50ETF', '510300.SH':'沪深300ETF', '159915.SZ':'创业板ETF'}


def validate_symbol(symbol):
    """显式交易所避免把深市股票误当上证证券，不自动修改用户输入。"""
    if not isinstance(symbol, str) or not re.fullmatch(r'\d{6}\.(SH|SZ)', symbol):
        raise ValueError('代码格式应为 588000.SH 或 002015.SZ')
    code, exchange = symbol.split('.')
    expected = 'SH' if code[0] in '56' else 'SZ' if code[0] in '013' else None
    if expected is None:
        raise ValueError('当前下载仅支持沪深股票及基金代码')
    if exchange != expected:
        raise ValueError(f'交易所不匹配，请使用 {code}.{expected}')
    return symbol


def resolve_instrument(symbol):
    """腾讯报价响应校验代码并提供名称；未知/已退市且无报价的代码拒绝下载。"""
    validate_symbol(symbol)
    key = symbol[-2:].lower()+symbol[:6]
    request = Request('https://qt.gtimg.cn/q='+key, headers={'User-Agent':'Mozilla/5.0'})
    with urlopen(request, timeout=15) as response:
        raw = response.read().decode('gbk')
    match = re.search(r'v_'+key+r'="([^"]+)"', raw)
    fields = match.group(1).split('~') if match else []
    if len(fields) < 4 or fields[2] != symbol[:6] or not fields[1].strip():
        raise ValueError('数据源未确认该证券代码，请检查代码或稍后重试')
    kind = 'etf' if symbol in VERIFIED_ETFS or 'ETF' in fields[1].upper() else 'stock' if symbol[0] in '036' else 'unknown'
    return dict(symbol=symbol, name=fields[1].strip(), kind=kind)


def describe(symbol, metadata=None):
    metadata = metadata or {}
    kind = 'etf' if symbol in VERIFIED_ETFS else 'index' if symbol == '000001.SH' else metadata.get('kind', 'stock' if re.fullmatch(r'(?:[036]\d{5})\.(?:SZ|SH)', symbol) else 'unknown')
    supported = symbol in VERIFIED_ETFS
    return dict(symbol=symbol, name=VERIFIED_ETFS.get(symbol, '上证指数' if symbol=='000001.SH' else metadata.get('name', symbol)),
                kind=kind, backtest_supported=supported,
                reason='' if supported else '当前仅支持已验证的三只境内 ETF 回测；该证券仅提供行情')


def instrument_catalog(root):
    from .workbench import datasets
    return [dict(item, dataset_id=dataset['id']) for dataset in datasets(root) for item in dataset['instruments']]


class DownloadManager:
    """独立单线程下载队列，SQLite 保存历史；失败可重新提交，重启不自动重试。"""
    def __init__(self, root, state_dir, downloader=None, resolver=None):
        self.root, self.state_dir = Path(root), Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.downloader, self.resolver = downloader or download_market, resolver or resolve_instrument
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
        from .workbench import datasets
        if not isinstance(request, dict) or set(request) != {'symbol','start','end'}:
            raise ValueError('新增代码需要 symbol、start、end')
        validate_symbol(request['symbol'])
        try:
            for key in ('start','end'):
                if date.fromisoformat(request[key]).isoformat() != request[key]:
                    raise ValueError
        except (ValueError, TypeError):
            raise ValueError('下载日期格式应为 YYYY-MM-DD') from None
        base = next((item for item in datasets(self.root) if item['id']=='real'), None)
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
        from .workbench import verify_manifests
        base = self.root/'data'/'real'
        verify_manifests(base)
        stage = self.root/'data'/('.download_'+identifier)
        stage.mkdir(parents=True)
        # 基线在复制前后必须稳定；发布只改新版本，绝不替换 data/real。
        names = ('market.csv','breadth.csv','manifest.json','market_manifest.json')
        hashes = {name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names if (base/name).is_file()}
        for name in hashes:
            shutil.copyfile(base/name, stage/name)
        if any(hashlib.sha256((base/name).read_bytes()).hexdigest()!=digest or hashlib.sha256((stage/name).read_bytes()).hexdigest()!=digest for name,digest in hashes.items()):
            raise ValueError('基线数据在复制时变化，请重试')
        verify_manifests(stage)
        metadata = self.resolver(request['symbol'])
        if metadata.get('symbol') != request['symbol']:
            raise ValueError('证券元数据代码不匹配')
        old_manifest = json.loads((stage/'market_manifest.json').read_text()) if (stage/'market_manifest.json').exists() else {}
        config_path = self.root/'configs'/'real_breadth.toml'
        config = tomllib.loads(config_path.read_text()) if config_path.is_file() else {}
        # 清单优先于配置；缺少证据时禁止猜测复权方式，避免混合价格口径。
        adjustment = old_manifest.get('adjustment', config.get('data', {}).get('adjustment'))
        if adjustment not in ('none','qfq'):
            raise ValueError('基线复权方式未知，无法安全合并行情')
        download = stage/'download'
        download.mkdir()
        shutil.copyfile(stage/'breadth.csv', download/'breadth.csv')
        self.downloader(request['start'], request['end'], download, symbols=[request['symbol']], adjustment=adjustment)
        incoming = pd.read_csv(download/'market.csv')
        existing = pd.read_csv(stage/'market.csv')
        expected = set(existing.loc[(existing.symbol=='000001.SH') & existing.date.between(request['start'],request['end']), 'date'])
        actual = set(incoming.loc[incoming.symbol==request['symbol'],'date'])
        if not expected or actual != expected:
            raise ValueError('目标证券与基线交易日不一致（可能停牌或上市时间不足），未发布')
        # 同一证券整段替换，避免不同时点前复权价格拼接造成虚假跳变。
        merged = pd.concat([existing[existing.symbol!=request['symbol']], incoming[incoming.symbol==request['symbol']]], ignore_index=True).sort_values(['date','symbol'])
        merged.to_csv(stage/'market.csv', index=False)
        downloaded_manifest = json.loads((download/'market_manifest.json').read_text())
        if downloaded_manifest.get('raw_dir'):
            downloaded_manifest['raw_dir'] = str(Path(downloaded_manifest['raw_dir']).relative_to(stage))
        # 两份下载清单使用同一相对路径，原子发布重命名后仍能找到原始响应。
        downloaded_manifest['raw_dir_base'] = 'dataset_root'
        (download/'market_manifest.json').write_text(json.dumps(downloaded_manifest, ensure_ascii=False, indent=2))
        parent_provenance = {key: old_manifest[key] for key in ('raw_dir', 'raw_sha256') if key in old_manifest}
        if parent_provenance.get('raw_dir'):
            parent_path = Path(parent_provenance['raw_dir'])
            # 旧 CLI 使用 --output data/real 时记录项目根相对路径，不能再次拼 data/real。
            # 其他未声明基准的旧相对路径保留原文，避免猜测一个错误的审计位置。
            if parent_path.is_absolute():
                parent_provenance['raw_dir_base'] = 'absolute'
            elif old_manifest.get('raw_dir_base') == 'dataset_root':
                parent_provenance['raw_dir'] = str((base/parent_path).resolve())
                parent_provenance['raw_dir_base'] = 'absolute'
            elif parent_path.parts[:2] == ('data', 'real') or old_manifest.get('raw_dir_base') == 'project_root':
                parent_provenance['raw_dir'] = str((self.root/parent_path).resolve())
                parent_provenance['raw_dir_base'] = 'absolute'
            else:
                parent_provenance['raw_dir_base'] = 'unknown'
        manifest = dict(old_manifest, source='managed baseline + tencent.newfqkline', adjustment=adjustment,
                        market_sha256=hashlib.sha256((stage/'market.csv').read_bytes()).hexdigest(),
                        parent_dataset='real', parent_hashes=hashes, download=downloaded_manifest,
                        parent_provenance=parent_provenance,
                        instruments={request['symbol']:metadata}, updated_symbol=request['symbol'],
                        symbols=sorted(merged.symbol.unique().tolist()), rows=len(merged),
                        symbol_sources={symbol: downloaded_manifest if symbol==request['symbol'] else {'dataset':'real','market_sha256':hashes['market.csv']} for symbol in merged.symbol.unique()},
                        warnings=list(old_manifest.get('warnings', []))+['新增证券只覆盖下载区间；同代码旧行情整段移除，避免前复权基准拼接。',
                            '仅三只已验证 ETF 支持回测。基线与新增行情分别保留来源；历史基线量额单位可能未经验证，成交量因子结果须谨慎解读。'])
        # 混合版本不能把某一次下载的量额单位冒充为整个数据集的统一声明。
        manifest.pop('volume_unit', None)
        manifest.pop('amount_unit', None)
        manifest.pop('raw_dir', None)
        manifest.pop('raw_sha256', None)
        (stage/'market_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        verify_manifests(stage)
        dataset_id = 'managed_'+identifier
        stage.rename(self.root/'data'/dataset_id)
        return dataset_id

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
