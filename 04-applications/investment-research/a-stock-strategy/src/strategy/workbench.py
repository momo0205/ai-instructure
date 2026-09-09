"""本地回测服务：只读取登记数据，执行时冻结输入，不发起网络请求。"""
from pathlib import Path
from datetime import date
from dataclasses import asdict
from .fees import STOCK_SUPPORTED_FROM
from .tradability import TRADABILITY_VERSION
import hashlib
import json
import shutil
import tomllib
import pandas as pd
from .registry import get_strategy_definition
from .validation import numeric
from .data import CsvMarketDataProvider
from .breadth import load_breadth, attach_breadth
from .backtest import BacktestEngine
from .evaluation import evaluate


def verify_manifests(folder):
    """拒绝更新中或损坏的数据/清单组合；旧清单无哈希时不声称已验证。"""
    folder = Path(folder)
    for manifest_name, filename, field in (
        ('market_manifest.json', 'market.csv', 'market_sha256'),
        ('manifest.json', 'breadth.csv', 'breadth_sha256'),
    ):
        path = folder/manifest_name
        if path.is_file():
            manifest = json.loads(path.read_text())
            expected = manifest.get(field)
            if expected is not None and expected != hashlib.sha256((folder/filename).read_bytes()).hexdigest():
                raise ValueError(f'{filename} hash mismatch：数据正在更新或清单已过期，请重新下载后重试')


def datasets(project_root):
    """列出实际存在的数据集；样例数据始终明确标记。"""
    result = []
    managed = sorted(p.name for p in (Path(project_root)/'data').glob('managed_*') if p.is_dir())
    for name in ('real','mvp_sample', *managed):
        folder = Path(project_root)/'data'/name
        if not all((folder/f).is_file() for f in ('market.csv','breadth.csv')):
            continue
        verify_manifests(folder)
        market = CsvMarketDataProvider(folder/'market.csv').load()
        breadth = load_breadth(folder/'breadth.csv')
        index_calendar = market.loc[market.symbol == '000001.SH', 'date']
        if index_calendar.empty:
            continue
        config_path = Path(project_root)/'configs'/('real_breadth.toml' if name=='real' else 'mvp.toml')
        config = tomllib.loads(config_path.read_text()) if config_path.is_file() else {}
        provenance = config.get('metadata',{})
        market_manifest_path = folder/'market_manifest.json'
        market_manifest = json.loads(market_manifest_path.read_text()) if market_manifest_path.is_file() else {}
        market_source = market_manifest.get('source', config.get('data',{}).get('source','unknown'))
        warnings = list(market_manifest.get('warnings', provenance.get('warnings',['数据质量未经独立验证'])))
        # 旧快照保留原文及哈希；展示时注明历史能力说明，避免与当前目录矛盾。
        warnings = [w.replace('仅三只已验证 ETF 支持回测。', '此版本创建时仅开放 ETF；当前支持范围以标的目录为准。') for w in warnings]
        if name=='mvp_sample':
            warnings.insert(0,'合成样例，不代表真实市场表现')
        result.append(dict(id=name,name='真实市场数据' if name=='real' else '合成样例',start=index_calendar.min().date().isoformat(),end=index_calendar.max().date().isoformat(),symbols=sorted(market.symbol.unique().tolist()),source=sorted(breadth.source.unique().tolist()),market_source=market_source,adjustment=market_manifest.get('adjustment',config.get('data',{}).get('adjustment','unknown')),sample=name=='mvp_sample',warnings=warnings))
        from .instruments import describe
        metadata = market_manifest.get('instruments', {})
        result[-1]['instruments'] = [dict(describe(symbol, metadata.get(symbol)),
            start=rows.date.min().date().isoformat(), end=rows.date.max().date().isoformat())
            for symbol, rows in market.groupby('symbol')]
        if name.startswith('managed_'):
            symbol = market_manifest.get('updated_symbol', '')
            result[-1]['name'] = f'行情版本 · {symbol} · {name[-8:]}'
    return result


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


def execute(root, request, output_dir):
    """冻结文件后运行。区间前行情仅预热指标，不产生订单或净值；收盘信号次日开盘成交。"""
    request = validate_request(root,request)
    dataset = next(d for d in datasets(root) if d['id']==request['dataset_id'])
    output = Path(output_dir)
    snapshot = output/'snapshot'
    snapshot.mkdir(parents=True,exist_ok=True)
    source = Path(root)/'data'/request['dataset_id']
    hashes = {}
    files = [(source/f,f) for f in ('market.csv','breadth.csv','manifest.json','market_manifest.json') if (source/f).is_file()]
    frozen_code = Path(root)/'src'/'strategy'
    package = frozen_code if frozen_code.is_dir() else Path(__file__).parent
    files += [(p,'code/'+str(p.relative_to(package))) for p in package.rglob('*.py')]
    for src,relative in files:
        destination = snapshot/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,destination)
        hashes[relative] = hashlib.sha256(destination.read_bytes()).hexdigest()
    encoded = json.dumps(request,ensure_ascii=False,sort_keys=True,allow_nan=False)
    verify_manifests(snapshot)
    (snapshot/'request.json').write_text(encoded)
    hashes['request.json'] = hashlib.sha256(encoded.encode()).hexdigest()
    market = CsvMarketDataProvider(snapshot/'market.csv').load()
    breadth = load_breadth(snapshot/'breadth.csv')
    definition = get_strategy_definition(request['strategy_id'])
    symbols = definition.symbols(request['parameters'])
    # 交易日历仅由指数及本次候选标的构成，其他数据行不得延长持有期。
    market = market[market.symbol.isin(['000001.SH',*symbols])].copy()
    market = attach_breadth(market,breadth,'000001.SH')
    warnings = list(dataset['warnings'])
    instrument_types = {item['symbol']:item['kind'] for item in dataset['instruments'] if item['symbol'] in symbols}
    has_stocks = 'stock' in instrument_types.values()
    if has_stocks:
        warnings += [
            '股票日频近似研究：停牌、涨跌停及历史 ST/退市状态可能未知；False 仅按可成交假设处理，不代表已验证。',
            '按开盘价加减滑点、全额成交估算；不模拟排队、部分成交或流动性容量。已知停牌阻断交易，买入涨停取消、卖出跌停顺延。',
            '股票买入按100股整手，至少下一交易日卖出；佣金含交易规费，另加双边过户费及卖出印花税。',
            '前复权价不是实际成交价，股票数量、最低佣金及税费金额均为近似；未独立模拟分红、送转和配股现金流。' if dataset['adjustment']=='qfq' else
            '未复权行情未独立模拟分红、送转、配股和持股数量变化，跨除权期间的收益可能失真。',
        ]
    needed = definition.warmup_sessions(request['parameters'])
    for symbol in symbols:
        count = len(market[(market.symbol==symbol)&(market.date<pd.Timestamp(request['start']))])
        if count<needed:
            warnings.append(f'warmup insufficient: {symbol} has {count}/{needed} prior sessions；早期信号可能无法选股')
    engine_keys = ('initial_cash','holding_period_days','min_declining_count','trigger_return_threshold','commission_rate','minimum_commission','slippage_bps')
    engine = BacktestEngine(lot_size=100,stamp_duty_rate=0.0,instrument_types=instrument_types,**{k:request[k] for k in engine_keys})
    result = engine.run(market,definition.build(request['parameters']),start=date.fromisoformat(request['start']),end=date.fromisoformat(request['end']))
    metadata = dict(dataset_id=request['dataset_id'],hashes=hashes,strategy_version=definition.version,breadth_source=sorted(breadth.source.unique().tolist()),market_source=dataset['market_source'],adjustment=dataset['adjustment'],sample=request['dataset_id']=='mvp_sample',code_provenance='Python source captured for audit; running service uses modules loaded at startup',timing='close signal; next session open execution',stamp_duty_rate=engine.stamp_duty_rate,lot_size=engine.lot_size)
    metadata.update(execution_mode='approximate',instrument_types=instrument_types,
                    trading_rules_version='cn-mainboard-daily-v1',
                    stamp_duty_rate=None if has_stocks else 0.0,
                    cost_policy=engine.fee_rules.metadata(),
                    tradability_rules_version=TRADABILITY_VERSION,
                    tradability='input flags only; unknown flags assumed executable; no auction order-book evidence')
    payload = dict(metrics=asdict(evaluate(result)),equity=[asdict(x) for x in result.equity],trades=[asdict(x) for x in result.trades],events=result.events,execution_events=result.execution_events,warnings=warnings+result.warnings,metadata=metadata,request=request)
    payload = json.loads(json.dumps(payload,default=str,ensure_ascii=False,allow_nan=False))
    (output/'result.json').write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False))
    return payload
