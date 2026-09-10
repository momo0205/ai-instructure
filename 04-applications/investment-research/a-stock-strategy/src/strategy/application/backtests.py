"""从已登记数据执行回测并保存审计结果。"""
from datetime import date
from dataclasses import asdict
import pandas as pd
from strategy.backtesting.tradability import TRADABILITY_VERSION
from strategy.strategies.registry import get_strategy_definition
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.market_data.breadth import load_breadth, attach_breadth
from strategy.backtesting.engine import BacktestEngine
from strategy.backtesting.evaluation import evaluate
from strategy.market_data.repository import datasets, verify_manifests
from strategy.application.requests import validate_request
from strategy.storage.snapshots import freeze_inputs, write_result


def execute(root, request, output_dir):
    """冻结文件后运行。区间前行情仅预热指标，不产生订单或净值；收盘信号次日开盘成交。"""
    request = validate_request(root,request)
    dataset = next(d for d in datasets(root) if d['id']==request['dataset_id'])
    snapshot, hashes = freeze_inputs(root, request, output_dir)
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
    return write_result(output_dir, payload)
