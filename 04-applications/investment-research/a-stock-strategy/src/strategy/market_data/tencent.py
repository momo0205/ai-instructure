"""腾讯日线下载与留痕。小候选池按年度请求，避免把大量抓取塞进回测流程。

显式区分上证指数 sh000001 与平安银行 sz000001。原始响应与清单保留，
遇到字段缺失、日期冲突或覆盖不足时不发布 market.csv。
"""
from datetime import date, datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

import pandas as pd
from strategy.market_data.csv import validate_market_frame

URL = 'https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get'


def parse_bars(payload, symbol, start, end, adjustment):
    """解析 OHLC 和原始量额：第 6 列为手，第 9 列为万元；第 7 列可能是对象。"""
    content = payload.get('data', {}).get(symbol, {})
    key = 'qfqday' if adjustment == 'qfq' and symbol != 'sh000001' else 'day'
    if key not in content:
        raise ValueError(f'{symbol}: missing {key}; refuse adjustment substitution')
    records = []
    for row in content[key]:
        if len(row) < 9:
            raise ValueError(f'{symbol}: missing turnover fields')
        if not start <= row[0] <= end:
            continue
        records.append(dict(date=row[0], symbol=symbol[2:]+'.'+symbol[:2].upper(),
                            open=float(row[1]), close=float(row[2]), high=float(row[3]), low=float(row[4]),
                            volume=float(row[5])*100, amount=float(row[8])*10000,
                            is_suspended=False, limit_up=False, limit_down=False))
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError(f'{symbol}: empty requested date range')
    frame = frame.drop_duplicates().sort_values('date').reset_index(drop=True)
    validate_market_frame(frame)
    if not ((frame.low <= frame[['open','close']].min(axis=1)) & (frame.high >= frame[['open','close']].max(axis=1))).all():
        raise ValueError(f'{symbol}: invalid OHLC relationship')
    if not frame[['volume','amount']].map(lambda x: pd.notna(x) and float('-inf') < x < float('inf') and x >= 0).all().all():
        raise ValueError(f'{symbol}: invalid volume/amount')
    return frame


def _request(params):
    request = Request(URL+'?'+urlencode(params), headers={'User-Agent':'Mozilla/5.0','Referer':'https://gu.qq.com/'})
    with urlopen(request, timeout=30) as response:
        text = response.read().decode('utf-8')
    # 接口返回 JavaScript 变量赋值。仅解析 JSON，绝不执行返回的脚本。
    begin = text.find('{')
    if begin < 0:
        raise ValueError('Tencent returned no JSON')
    return json.JSONDecoder().raw_decode(text[begin:])[0]


def download_market(start, end, output_dir, symbols=None, adjustment='none', requester=None):
    """下载指数和 ETF，并要求所有候选与指数日期完全一致。默认不复权执行价格。"""
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or last > date.today() or last.year-first.year > 30:
        raise ValueError('invalid date range')
    if adjustment not in ('none','qfq'):
        raise ValueError('adjustment must be none or qfq')
    symbols = symbols or ['000001.SH','588000.SH','510300.SH','159915.SZ']
    if '000001.SH' not in symbols:
        symbols = ['000001.SH', *symbols]
    if len(set(symbols)) != len(symbols) or len(symbols) > 30:
        raise ValueError('symbols must be unique, maximum 30')
    if any(not re.fullmatch(r'\d{6}\.(SH|SZ)', symbol) for symbol in symbols):
        raise ValueError('symbols require exchange suffix, e.g. 588000.SH')
    output = Path(output_dir)
    raw = output/'market_raw'/uuid4().hex
    raw.mkdir(parents=True)
    fetch = requester or _request
    frames, hashes = [], {}
    for symbol in symbols:
        prefixed = symbol[-2:].lower()+symbol[:6]
        for year in range(first.year,last.year+1):
            lo, hi = max(start,f'{year}-01-01'),min(end,f'{year}-12-31')
            params = {'_var':'kline_data','param':f'{prefixed},day,{lo},{hi},640,{"qfq" if adjustment=="qfq" else ""}'}
            if requester is None:
                time.sleep(.3)
            payload = fetch(params)
            path = raw/f'{symbol}-{year}.json'
            path.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            frames.append(parse_bars(payload,prefixed,lo,hi,adjustment))
    frame = pd.concat(frames).sort_values(['date','symbol']).reset_index(drop=True)
    validate_market_frame(frame)
    sessions = set(frame.loc[frame.symbol=='000001.SH','date'])
    if any(set(frame.loc[frame.symbol==s,'date']) != sessions for s in symbols):
        raise ValueError('candidate/index date coverage mismatch; market.csv not published')
    # 已有广度提供第二份交易日集合，可以识别供应商对整段日期的静默截断。
    breadth_path = output/'breadth.csv'
    if breadth_path.exists():
        breadth = pd.read_csv(breadth_path)
        expected = set(breadth.loc[breadth.date.between(start,end),'date'])
        if sessions != expected:
            raise ValueError('market/breadth date coverage mismatch; market.csv not published')
    manifest = dict(source='tencent.newfqkline',source_url=URL,adjustment=adjustment,start=start,end=end,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),symbols=symbols,rows=len(frame),
                    volume_unit='shares',amount_unit='CNY',raw_dir=str(raw),raw_sha256=hashes,
                    warnings=['停牌和涨跌停状态未提供；False 只表示未知。',
                              '不复权行情尚未计入分红现金流；前复权价只适合近似研究，不是实际成交价。'])
    temporary = output/'market.csv.tmp'
    frame.to_csv(temporary,index=False)
    manifest['market_sha256'] = hashlib.sha256(temporary.read_bytes()).hexdigest()
    manifest_path = output/'market_manifest.json'
    manifest_tmp = manifest_path.with_suffix('.json.tmp')
    manifest_tmp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(output/'market.csv')
    manifest_tmp.replace(manifest_path)
    return {'market':str(output/'market.csv'),'manifest':str(manifest_path),'rows':len(frame)}
