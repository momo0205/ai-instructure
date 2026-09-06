"""Historical market breadth from full daily A-share cross sections.

The minimum row count rejects obviously partial watchlists; it does NOT establish
universe completeness. Suspensions are absent from Tushare daily. Keep raw inputs
and audit exchange coverage/retired securities before interpreting backtests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen
from uuid import uuid4

import pandas as pd

_COLUMNS = ['date', 'declining_count', 'total_count', 'source', 'sh_count', 'sz_count', 'bj_count']
_REQUIRED = ['trade_date', 'ts_code', 'pct_chg']
_CODES = re.compile(r'(?:(?:600|601|603|605|688|689)\d{3}\.SH|(?:000|001|002|003|300|301|302)\d{3}\.SZ|(?:[48]\d{5}|920\d{3})\.BJ)')
_COVERAGE_NOTE = '最低样本数仅拦截明显不完整名单，不证明全市场完整；需核验各交易所、退市历史与停牌口径。'


def _date(value) -> str:
    text = str(value)
    if re.fullmatch(r'\d{8}', text):
        fmt = '%Y%m%d'
    elif re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        fmt = '%Y-%m-%d'
    else:
        raise ValueError('日期必须为 YYYYMMDD 或 YYYY-MM-DD')
    try:
        return datetime.strptime(text, fmt).date().isoformat()
    except ValueError:
        raise ValueError('日期无效') from None


def build_breadth(daily: pd.DataFrame, source: str, universe='SH_SZ_BJ', min_daily_records=4000) -> pd.DataFrame:
    """Count negative provider pct_chg; row threshold is not completeness proof."""
    if universe not in {'SH_SZ_BJ', 'SH_SZ'}:
        raise ValueError('universe 必须为 SH_SZ_BJ 或 SH_SZ')
    if not isinstance(source, str) or not source.strip():
        raise ValueError('source 必须注明数据来源')
    if isinstance(min_daily_records, bool) or not isinstance(min_daily_records, int) or min_daily_records < 1:
        raise ValueError('min_daily_records 必须为正整数')
    if not daily.columns.is_unique or not set(_REQUIRED).issubset(daily.columns):
        raise ValueError('原始行情需要唯一的 trade_date, ts_code, pct_chg 列')
    frame = daily[_REQUIRED].copy()
    frame['date'] = frame.trade_date.map(_date)
    if not frame.ts_code.map(lambda v: isinstance(v, str) and bool(_CODES.fullmatch(v))).all():
        raise ValueError('发现非 A 股代码或交易所不匹配，拒绝计算广度')
    if frame.duplicated(['date', 'ts_code']).any():
        raise ValueError('发现重复日期/股票代码')
    def valid_return(value):
        if isinstance(value, bool) or type(value).__name__ == 'bool_':
            return False
        try:
            return math.isfinite(float(value)) and float(value) >= -100
        except (ValueError, TypeError, OverflowError):
            return False
    if not frame.pct_chg.map(valid_return).all():
        raise ValueError('pct_chg 必须为有限数值且不低于 -100%')
    frame['pct_chg'] = frame.pct_chg.astype(float)
    frame['exchange'] = frame.ts_code.str[-2:]
    if universe == 'SH_SZ':
        frame = frame[frame.exchange != 'BJ']
    rows = []
    for date, group in frame.groupby('date', sort=True):
        if len(group) < min_daily_records:
            raise ValueError(f'{date} 仅 {len(group)} 条行情，少于最低样本数 {min_daily_records}；拒绝部分名单')
        counts = group.exchange.value_counts()
        rows.append({'date': date, 'declining_count': int((group.pct_chg < 0).sum()),
                     'total_count': len(group), 'source': source,
                     'sh_count': int(counts.get('SH', 0)), 'sz_count': int(counts.get('SZ', 0)),
                     'bj_count': int(counts.get('BJ', 0))})
    return pd.DataFrame(rows, columns=_COLUMNS)


def _request(payload):
    request = Request('https://api.tushare.pro', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def _write_csv(frame, path):
    temporary = path.with_suffix('.csv.tmp')
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def download_tushare_daily(start, end, output_dir, token=None, requester=None, *,
                           sleeper=time.sleep, min_daily_records=4000):
    """Download daily cross sections with raw caches and publish breadth + manifest.

    requester(payload) returns a Tushare response dict. Tokens are read from
    TUSHARE_TOKEN when omitted and never persisted. Each call sleeps 1.3 seconds
    to respect the free tier's 50 requests/minute. Empty weekdays are recorded,
    not asserted to be exchange holidays. Failure never publishes partial output.
    """
    token = token if token is not None else os.environ.get('TUSHARE_TOKEN')
    if not isinstance(token, str) or not token.strip():
        raise ValueError('请先设置 TUSHARE_TOKEN；需要本人 Tushare 股票日线访问权限')
    token = token.strip()
    first, last = _date(start), _date(end)
    if first > last:
        raise ValueError('开始日期不能晚于结束日期')
    output = Path(output_dir)
    raw_dir = output / 'raw' / uuid4().hex
    raw_dir.mkdir(parents=True, exist_ok=False)
    requester = requester or _request
    frames, empty_dates, hashes = [], [], {}
    day, stop = datetime.fromisoformat(first), datetime.fromisoformat(last)
    while day <= stop:
        date = day.date().isoformat()
        day += timedelta(days=1)
        if datetime.fromisoformat(date).weekday() >= 5:
            continue
        pages = []
        for page in range(20):
            sleeper(1.3)
            payload = {'api_name': 'daily', 'token': token,
                       'params': {'trade_date': date.replace('-', ''), 'limit': 6000, 'offset': page * 6000},
                       'fields': ','.join(_REQUIRED)}
            try:
                response = requester(payload)
            except Exception:
                raise ValueError(f'Tushare 网络请求失败（{date}）；未发布部分广度，请重试') from None
            if not isinstance(response, dict) or response.get('code') != 0:
                message = str(response.get('msg', '无效响应')) if isinstance(response, dict) else '无效响应'
                raise ValueError(f'Tushare API 错误（{date}）：{message.replace(token, "[REDACTED]")}') from None
            data = response.get('data')
            if not isinstance(data, dict) or not isinstance(data.get('fields'), list) or not isinstance(data.get('items'), list):
                raise ValueError(f'Tushare 响应格式错误（{date}）')
            fields, items = data['fields'], data['items']
            if len(set(fields)) != len(fields) or not set(_REQUIRED).issubset(fields):
                raise ValueError(f'Tushare 响应缺少行情列（{date}）')
            try:
                frame = pd.DataFrame(items, columns=fields)
            except (ValueError, TypeError):
                raise ValueError(f'Tushare 响应行格式错误（{date}）') from None
            if len(frame) > 6000:
                raise ValueError('Tushare 分页超出声明上限')
            if not frame.empty and not frame.trade_date.map(_date).eq(date).all():
                raise ValueError('Tushare 返回日期与请求日期不一致')
            pages.append(frame)
            if len(frame) < 6000:
                break
        else:
            raise ValueError('Tushare 分页未结束，拒绝可能截断的数据')
        daily = pd.concat(pages, ignore_index=True)
        # Validate each entire day's result before caching, including cross-page duplicates.
        build_breadth(daily, 'tushare.daily', min_daily_records=min_daily_records)
        raw_path = raw_dir / f'{date}.csv'
        _write_csv(daily, raw_path)
        hashes[date] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        if daily.empty:
            empty_dates.append(date)
        else:
            frames.append(daily)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=_REQUIRED)
    breadth = build_breadth(combined, 'tushare.daily', min_daily_records=min_daily_records)
    manifest = {'source': 'tushare.daily', 'source_url': 'https://tushare.pro/document/2?doc_id=27',
                'retrieved_at': datetime.now(timezone.utc).isoformat(), 'start': first, 'end': last,
                'universe': 'SH_SZ_BJ', 'coverage_dates': breadth.date.tolist(), 'empty_dates': empty_dates,
                'min_daily_records': min_daily_records, 'complete_universe_verified': False,
                'coverage_note': _COVERAGE_NOTE, 'raw_dir': str(raw_dir.resolve()), 'raw_sha256': hashes}
    breadth_path, manifest_path = output / 'breadth.csv', output / 'manifest.json'
    manifest_temp = output / 'manifest.json.tmp'
    manifest_temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    _write_csv(breadth, breadth_path)
    manifest_temp.replace(manifest_path)
    return {'breadth': breadth_path, 'manifest': manifest_path, 'raw_dir': raw_dir}
