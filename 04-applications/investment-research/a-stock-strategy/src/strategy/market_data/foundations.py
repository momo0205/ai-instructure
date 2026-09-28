"""Publish immutable index and breadth snapshots with retained provider evidence."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import shutil
import pandas as pd
from strategy.market_data.tencent import download_market
from strategy.market_data.ingest import download_tushare_daily
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.market_data.breadth import load_breadth
from strategy.market_data.repository import verify_manifests
from strategy.validation import UserError


def _reject(message):
    raise UserError('DATA_VALIDATION_FAILED', message)


def _manifest(folder, name, field, stage, breadth=False):
    manifest=json.loads((folder/name).read_text())
    if not isinstance(manifest.get('source'),str) or not manifest['source'].strip():
        _reject('基础数据清单缺少来源')
    if not re.fullmatch(r'[0-9a-f]{64}',str(manifest.get(field,''))):
        _reject('基础数据清单缺少有效哈希')
    verify_manifests(folder)
    raw=Path(manifest.get('raw_dir','')).resolve()
    if not raw.is_dir() or not raw.is_relative_to(folder.resolve()) or raw.is_symlink():
        _reject('原始证据必须位于本次下载目录')
    hashes=manifest.get('raw_sha256')
    if not isinstance(hashes,dict) or not hashes: _reject('原始证据缺少哈希')
    if any(p.is_symlink() for p in raw.rglob('*')): _reject('原始证据不允许符号链接')
    for key,digest in hashes.items():
        path=(raw/(key+'.csv' if breadth else key)).resolve()
        if not path.is_relative_to(raw) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            _reject('原始证据哈希不一致')
    manifest.update(raw_dir=str(raw.relative_to(stage.resolve())),raw_dir_base='dataset_root')
    return manifest


def update_foundation(root, identifier, start, end, *, token=None, progress=None,
                      market_downloader=None, breadth_downloader=None):
    if not isinstance(identifier,str) or not re.fullmatch(r'[0-9a-f]+',identifier):
        _reject('invalid foundation identifier')
    data=Path(root)/'data'; data.mkdir(parents=True,exist_ok=True)
    stage=data/('.foundation_'+identifier); final=data/('foundation_'+identifier)
    if final.exists(): _reject('基础版本已存在')
    stage.mkdir()
    def report(phase,message):
        if progress: progress(dict(stage=phase,message=message))
    try:
        report('index','下载上证指数')
        (market_downloader or download_market)(start,end,stage/'index',symbols=['000001.SH'],adjustment='qfq',strict_calendar=False)
        report('breadth','下载全市场广度')
        if breadth_downloader is not None:
            breadth_downloader(start,end,stage/'breadth',token=token)
        else:
            download_tushare_daily(start,end,stage/'breadth',token=token,progress=progress)
        report('validating','验证日期覆盖与原始证据')
        market=_manifest(stage/'index','market_manifest.json','market_sha256',stage)
        breadth=_manifest(stage/'breadth','manifest.json','breadth_sha256',stage,True)
        if market.get('adjustment')!='qfq': _reject('基础指数复权口径不一致')
        index=CsvMarketDataProvider(stage/'index/market.csv').load()
        rows=load_breadth(stage/'breadth/breadth.csv')
        dates=set(index.date.dt.strftime('%Y-%m-%d'))
        if set(index.symbol)!= {'000001.SH'} or len(dates)<2 or dates!=set(rows.date.dt.strftime('%Y-%m-%d')):
            _reject('指数与广度日期不完整或不一致')
        if min(dates)<start or max(dates)>end: _reject('提供方返回请求区间外日期')
        # 每个工作日必须有非空截面或已留存的空响应，不把边界缺失默认为节假日。
        empty=set(breadth.get('empty_dates',[]))
        expected=set(pd.bdate_range(start,end).strftime('%Y-%m-%d'))
        if breadth.get('start')!=start or breadth.get('end')!=end or set(breadth.get('coverage_dates',[]))!=dates or dates & empty or not expected.issubset(dates | empty):
            _reject('请求区间覆盖不完整，不能确认缺失日期为休市')
        if not (dates|empty).issubset(set(breadth['raw_sha256'])): _reject('逐日覆盖缺少原始响应')
        shutil.copyfile(stage/'index/market.csv',stage/'market.csv')
        shutil.copyfile(stage/'breadth/breadth.csv',stage/'breadth.csv')
        market.update(created_at=datetime.now(timezone.utc).isoformat(),foundation_id=final.name)
        for name,manifest in [('market_manifest.json',market),('manifest.json',breadth),
                              ('index/market_manifest.json',market),('breadth/manifest.json',breadth)]:
            (stage/name).write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        verify_manifests(stage)
        report('publishing','发布基础数据版本')
        stage.rename(final)
        return final.name
    except Exception:
        shutil.rmtree(stage,ignore_errors=True)
        raise
