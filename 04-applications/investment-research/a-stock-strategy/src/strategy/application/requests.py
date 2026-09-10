"""回测请求与数据覆盖约束。"""
from pathlib import Path
from datetime import date
import pandas as pd
from strategy.backtesting.fees import STOCK_SUPPORTED_FROM
from strategy.strategies.registry import get_strategy_definition
from strategy.validation import numeric
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.market_data.breadth import load_breadth
from strategy.market_data.repository import datasets


def validate_request(root, request):
    """严格校验日期、标的和参数。收益阈值用小数；滑点用基点，1 bp = 0.01%。"""
    defaults = dict(strategy_id='fixed_asset',parameters={},dataset_id='mvp_sample',start=None,end=None,initial_cash=100000.0,holding_period_days=1,min_declining_count=4000,trigger_return_threshold=-.01,commission_rate=.0003,minimum_commission=5.0,slippage_bps=2.0)
    if not isinstance(request,dict) or set(request)-set(defaults):
        raise ValueError('unknown request fields or invalid request')
    value = defaults | request
    available = {d['id']:d for d in datasets(root)}
    if not isinstance(value['dataset_id'],str) or value['dataset_id'] not in available:
        raise ValueError('unknown dataset_id')
    dataset = available[value['dataset_id']]
    definition = get_strategy_definition(value['strategy_id'])
    params = definition.normalize_parameters(value['parameters'])
    symbols = definition.symbols(params)
    if not isinstance(symbols,list) or not 1 <= len(symbols) <= 100 or any(not isinstance(s,str) or s not in dataset['symbols'] or s=='000001.SH' for s in symbols) or len(set(symbols))!=len(symbols):
        raise ValueError('parameters require unique available tradable symbols')
    supported = {item['symbol'] for item in dataset['instruments'] if item['backtest_supported']}
    if any(symbol not in supported for symbol in symbols):
        raise ValueError('该证券暂不支持回测：需为已验证 ETF 或已识别的普通沪深主板股票')
    value['parameters'] = params
    for key,minimum,maximum,integer in [('initial_cash',1,1e10,False),('holding_period_days',1,252,True),('min_declining_count',0,100000,True),('trigger_return_threshold',-1,1,False),('commission_rate',0,.1,False),('minimum_commission',0,10000,False),('slippage_bps',0,1000,False)]:
        value[key] = numeric(value[key],key,minimum,maximum,integer)
    for key in ('start','end'):
        value[key] = dataset[key] if value[key] is None else value[key]
        try:
            if not isinstance(value[key],str) or date.fromisoformat(value[key]).isoformat()!=value[key]:
                raise ValueError
        except (ValueError,TypeError):
            raise ValueError(f'invalid {key} date') from None
    if not dataset['start'] <= value['start'] <= value['end'] <= dataset['end']:
        raise ValueError('date range outside dataset coverage')
    if any(item['symbol'] in symbols and item['kind']=='stock' for item in dataset['instruments']) and value['start'] < STOCK_SUPPORTED_FROM.isoformat():
        raise ValueError('股票费用规则仅支持 2022-07-01 起的回测，请调整开始日期')
    market = CsvMarketDataProvider(Path(root)/'data'/value['dataset_id']/'market.csv').load()
    selected = market[market.date.between(pd.Timestamp(value['start']),pd.Timestamp(value['end']))]
    index_dates = set(selected.loc[selected.symbol=='000001.SH','date'])
    if not index_dates or any(set(selected.loc[selected.symbol==s,'date']) != index_dates for s in symbols):
        raise ValueError('symbol/date coverage incomplete')
    breadth = load_breadth(Path(root)/'data'/value['dataset_id']/'breadth.csv')
    breadth_dates = set(breadth.loc[breadth.date.between(pd.Timestamp(value['start']),pd.Timestamp(value['end'])),'date'])
    if breadth_dates != index_dates:
        raise ValueError('breadth/date coverage incomplete or inconsistent')
    return value
