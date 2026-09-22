"""独立行情资产：保存供应商证据，不要求指数或广度基线已经就绪。

每次下载发布不可变的新版本。覆盖检查只比较实际观测到的指数交易日，
没有完整交易日历时不会将请求边界或缺行解释为停牌。
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import shutil
import pandas as pd

from strategy.market_data.csv import CsvMarketDataProvider
from strategy.validation import UserError


def _fail(message):
    raise UserError('DATA_VALIDATION_FAILED', message)


def _identifier(value, published=False):
    pattern = r'asset_[A-Za-z0-9_-]+' if published else r'[A-Za-z0-9_-]+'
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        _fail('无效的行情版本编号')
    return value


def _safe_file(path, root):
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        _fail('行情证据路径无效或包含符号链接')
    return path


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class PreparedAsset:
    identifier: str
    stage: Path
    adjustment: str = 'qfq'


class AssetRepository:
    def __init__(self, root):
        self.root = Path(root)

    def list(self):
        return list_assets(self.root)

    def prepare(self, identifier):
        _identifier(identifier)
        data = self.root/'data'
        if data.is_symlink():
            _fail('数据目录不能是符号链接')
        data.mkdir(parents=True, exist_ok=True)
        if (data/('asset_'+identifier)).exists():
            _fail('行情版本已存在，不允许覆盖')
        stage = data/('.asset_download_'+identifier)
        stage.mkdir()
        (stage/'download').mkdir()
        return PreparedAsset(identifier, stage)

    def publish(self, prepared, request, metadata):
        _identifier(prepared.identifier)
        stage = self.root/'data'/('.asset_download_'+prepared.identifier)
        if prepared.stage != stage or stage.is_symlink() or not stage.is_dir():
            _fail('无效的行情暂存目录')
        download = stage/'download'
        if download.is_symlink():
            _fail('下载目录不能是符号链接')
        try:
            first, last = date.fromisoformat(request['start']), date.fromisoformat(request['end'])
        except (KeyError, TypeError, ValueError):
            _fail('下载日期无效')
        if first > last or last > date.today():
            _fail('下载日期区间无效或晚于今天')
        symbol = request['symbol']
        if not re.fullmatch(r'\d{6}\.(SH|SZ)', symbol) or metadata.get('symbol') != symbol:
            _fail('证券元数据代码不匹配')
        market = _safe_file(download/'market.csv', download)
        manifest = json.loads(_safe_file(download/'market_manifest.json', download).read_text())
        if not isinstance(manifest.get('source'), str) or not manifest['source'].strip():
            _fail('下载清单缺少数据来源')
        if manifest.get('market_sha256') != _digest(market):
            _fail('行情内容哈希不匹配')
        if manifest.get('adjustment') != prepared.adjustment:
            _fail('行情复权方式与下载请求不一致')
        frame = CsvMarketDataProvider(market).load()
        if frame.empty or symbol not in set(frame.symbol) or set(frame.symbol)-{symbol, '000001.SH'}:
            _fail('下载证券与请求不匹配或行情为空')
        if not frame.date.between(pd.Timestamp(first), pd.Timestamp(last)).all():
            _fail('行情包含请求区间外的记录')
        if not ((frame.low <= frame[['open','close']].min(axis=1)) & (frame.high >= frame[['open','close']].max(axis=1))).all():
            _fail('行情 OHLC 关系无效')
        for column in ('volume','amount'):
            values = pd.to_numeric(frame[column], errors='coerce')
            if not values.map(lambda x: pd.notna(x) and 0 <= x < float('inf')).all():
                _fail('行情成交量或金额无效')
        # 相对原始响应路径以下载目录为基准；发布后统一变为资产根相对路径。
        if manifest.get('raw_dir'):
            raw_path = Path(manifest['raw_dir'])
            raw = raw_path if raw_path.is_absolute() else download/raw_path
            if raw.is_symlink() or not raw.is_dir() or not raw.resolve().is_relative_to(download.resolve()):
                _fail('原始响应目录必须位于本次下载目录内')
            if any(p.is_symlink() for p in raw.rglob('*')):
                _fail('原始响应不允许符号链接')
            hashes = manifest.get('raw_sha256')
            if not isinstance(hashes, dict) or not hashes:
                _fail('原始响应缺少哈希')
            actual_files = {str(p.relative_to(raw)) for p in raw.rglob('*') if p.is_file()}
            if set(hashes) != actual_files:
                _fail('原始响应文件与哈希清单不一致')
            for name, digest in hashes.items():
                if _digest(_safe_file(raw/name, raw)) != digest:
                    _fail('原始响应哈希不匹配')
            shutil.copytree(raw, stage/'raw')
            manifest.update(raw_dir='raw', raw_dir_base='dataset_root')
        elif manifest.get('raw_sha256'):
            _fail('原始响应目录缺失')
        selected = frame[frame.symbol == symbol]
        sessions = set(frame.loc[frame.symbol == '000001.SH','date'].dt.strftime('%Y-%m-%d'))
        observed = set(selected.date.dt.strftime('%Y-%m-%d'))
        missing = sorted(sessions-observed)
        status = 'gaps_detected' if missing else 'matches_observed_index' if sessions else 'calendar_unverified'
        warnings = list(manifest.get('warnings', []))
        warnings.append('覆盖仅与本次观测指数比较；尚未由完整交易日历验证请求区间。')
        if missing:
            warnings.append('部分观测指数交易日缺少该证券行情；原因未知，不能据此认定停牌。')
        if not sessions:
            warnings.append('本次没有指数交易日参照，行情完整性尚未验证。')
        manifest.update(asset=True, updated_symbol=symbol, instruments={symbol:metadata},
                        requested_start=request['start'], requested_end=request['end'],
                        created_at=datetime.now(timezone.utc).isoformat(),
                        quality=dict(missing_dates=missing, coverage_status=status), warnings=warnings)
        shutil.copyfile(market, stage/'market.csv')
        (stage/'market_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        shutil.rmtree(download)
        target = self.root/'data'/('asset_'+prepared.identifier)
        if target.exists() or target.is_symlink():
            _fail('行情版本已存在，不允许覆盖')
        stage.rename(target)
        return target.name


_CACHE = {}


def detail_asset(root, identifier):
    """只接受版本编号，不接受客户端路径；缓存按 CSV/清单统计信息失效。"""
    _identifier(identifier, published=True)
    folder = Path(root)/'data'/identifier
    if folder.is_symlink() or (Path(root)/'data').is_symlink():
        _fail('行情目录不能是符号链接')
    market = _safe_file(folder/'market.csv', folder)
    manifest_path = _safe_file(folder/'market_manifest.json', folder)
    key = str(folder.resolve())
    stamp = tuple((p.stat().st_mtime_ns, p.stat().st_size, p.stat().st_ino) for p in (market,manifest_path))
    if key in _CACHE and _CACHE[key][0] == stamp:
        return json.loads(json.dumps(_CACHE[key][1]))
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('market_sha256') != _digest(market):
        _fail('行情内容哈希不匹配')
    symbol = manifest['updated_symbol']
    frame = CsvMarketDataProvider(market).load()
    rows = frame[frame.symbol == symbol].copy()
    if rows.empty:
        _fail('行情版本缺少目标证券')
    metadata = manifest.get('instruments', {}).get(symbol, {})
    rows['date'] = rows.date.dt.strftime('%Y-%m-%d')
    result = dict(id=identifier, symbol=symbol, name=metadata.get('name',symbol), kind=metadata.get('kind','unknown'),
                  adjustment=manifest.get('adjustment','unknown'), source=manifest.get('source','unknown'),
                  requested_start=manifest.get('requested_start'),requested_end=manifest.get('requested_end'),
                  start=rows.date.min(),end=rows.date.max(),rows=len(rows),created_at=manifest.get('created_at'),
                  warnings=manifest.get('warnings',[]),quality=manifest.get('quality',{}),
                  preview=json.loads(rows.tail(100).to_json(orient='records')),
                  manifest={k:manifest[k] for k in ('source','source_url','market_sha256','raw_sha256','raw_dir','raw_dir_base','retrieved_at','volume_unit','amount_unit') if k in manifest})
    _CACHE[key] = stamp,result
    return json.loads(json.dumps(result))


def list_assets(root):
    result = []
    for folder in sorted((Path(root)/'data').glob('asset_*')):
        detail = detail_asset(root,folder.name)
        result.append({k:v for k,v in detail.items() if k not in ('preview','manifest')})
    return result
