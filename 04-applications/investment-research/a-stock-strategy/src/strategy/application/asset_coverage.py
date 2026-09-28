"""证券覆盖只在同一行情版本内计算，不拼接不同前复权基准。"""
from functools import lru_cache
from pathlib import Path
import pandas as pd
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.market_data.coverage import segments
from strategy.market_data.catalog import describe


@lru_cache(maxsize=128)
def _load(path,mtime,size):
    return CsvMarketDataProvider(path).load()


def asset_coverage(root,asset,index,last_day):
    path=Path(root)/'data'/asset.get('dataset_id',asset['id'])/'market.csv'
    stat=path.stat();frame=_load(str(path.resolve()),stat.st_mtime_ns,stat.st_size)
    dates=set(frame.loc[frame.symbol==asset['symbol'],'date'].dt.strftime('%Y-%m-%d'))
    observed_index=set(index.index.date.dt.strftime('%Y-%m-%d'))
    breadth=set(index.breadth.date.dt.strftime('%Y-%m-%d'))
    instrument=describe(asset['symbol'],asset)
    minimum=instrument.get('backtest_start') or asset['start']
    usable={d for d in dates&observed_index&breadth if minimum<=d<=last_day}
    if not instrument['backtest_supported'] or asset.get('adjustment')!='qfq':usable=set()
    research=[span for span in segments(usable,closed_dates=index.closed_dates) if span['days']>=2]
    expected={d.date().isoformat() for d in pd.bdate_range(asset['start'],min(asset['end'],last_day))}-index.closed_dates
    missing=[]
    for reason,values in [('缺少证券行情',expected-dates),('缺少指数行情',expected-observed_index),('缺少市场广度',expected-breadth)]:
        missing.extend(dict(span,reason=reason) for span in segments(values,closed_dates=index.closed_dates))
    return dict(market=segments(dates,closed_dates=index.closed_dates),research=research,missing=missing,
                warnings=['数据共同覆盖；策略预热窗口及交易约束仍需在提交回测时检查。','不同前复权行情版本不自动拼接。'])
