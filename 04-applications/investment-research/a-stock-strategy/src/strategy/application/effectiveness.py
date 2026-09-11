"""固定标的的历史对照实验；只替换入场计划，撮合与费用仍由统一引擎执行。"""
from dataclasses import asdict, replace
import random
import pandas as pd

from strategy.application.simulation import run_simulation
from strategy.strategies.fixed import FixedAssetStrategy

VERSION = 'fixed-timing-controls-v1'
SEED = 20260910
TRIALS = 100


def schedule_indices(session_count, holding_days, count, rng):
    """均匀抽取固定笔数的不重叠计划，返回收盘信号的交易日下标。

    signal=s, entry=s+1, exit=s+1+h；允许卖出当日收盘形成下一信号。
    移除相邻窗口强制间距后抽组合，再恢复间距，避免贪心采样偏向区间前部。
    """
    if count == 0:
        return []
    population = session_count - holding_days - 1 - holding_days * (count - 1)
    if count < 0 or holding_days < 1 or population < count:
        raise ValueError('cannot fit requested non-overlapping trades')
    compressed = sorted(rng.sample(range(population), count))
    return [value + i * holding_days for i, value in enumerate(compressed)]


class ScheduledFixedAsset:
    """保留固定策略的当日证券状态过滤，仅用预先抽好的日期替代市场触发条件。"""
    def __init__(self, symbol, signals):
        self.fixed = FixedAssetStrategy(symbol)
        self.signals = frozenset(signals)

    def select(self, as_of, market, universe):
        if as_of not in self.signals:
            return None
        return self.fixed.select(as_of, replace(market, triggered=True), universe)


def compare_effectiveness(plan, symbol, observed, *, trials=TRIALS, seed=SEED):
    """返回可审计的描述性对照，不将历史百分位当作显著性或未来收益保证。"""
    count = len(observed['trades'])
    dates = sorted({pd.Timestamp(d).date() for d in plan.market.date
                    if (plan.start is None or pd.Timestamp(d).date() >= plan.start)
                    and (plan.end is None or pd.Timestamp(d).date() <= plan.end)})
    if len(dates)<3:
        return dict(status='unavailable',reason_code='INSUFFICIENT_SESSIONS',message='至少需要 3 个交易日，才能按次日开盘买入并在期末卖出。')
    holding = plan.engine_options['holding_period_days']
    rng = random.Random(seed)
    # 保留完整市场输入及全部执行选项，只替换计划与持有期。
    def simulate(signals, period):
        return run_simulation(replace(plan, strategy=ScheduledFixedAsset(symbol, signals),
                                      engine_options={**plan.engine_options, 'holding_period_days':period}))
    benchmark = simulate([dates[0]], len(dates)-2)
    benchmark_payload = dict(metrics=asdict(benchmark.metrics),
                             equity=[asdict(p) for p in benchmark.result.equity],
                             trades=[asdict(t) for t in benchmark.result.trades],
                             execution_events=benchmark.result.execution_events,
                             warnings=benchmark.result.warnings)
    if not count:
        return dict(status='available', version=VERSION, symbol=symbol, seed=seed, trials=0,
                    target_trade_count=0, holding_period_days=holding,
                    strategy_metrics=observed['metrics'], buy_and_hold=benchmark_payload,
                    random=dict(status='unavailable', reason_code='NO_COMPLETED_TRADES',
                                message='原策略没有完成交易，仅展示买入持有基准；随机择时没有可匹配的交易笔数。'),
                    limitations=['买入持有从次日开盘买入，期末开盘计划卖出；沿用本次资金、费用及数据近似，可能因交易约束未成交。'])
    samples = []
    for _ in range(trials):
        signals = [dates[i] for i in schedule_indices(len(dates), holding, count, rng)]
        outcome = simulate(signals, holding)
        samples.append(dict(signal_dates=[d.isoformat() for d in signals],
                            cumulative_return=outcome.metrics.cumulative_return,
                            max_drawdown=outcome.metrics.max_drawdown,
                            trade_count=outcome.metrics.trade_count,
                            cash_ratio=outcome.metrics.cash_ratio,
                            open_position=bool(outcome.result.equity[-1].position_value)))
    returns = [s['cumulative_return'] for s in samples]
    actual = observed['metrics']['cumulative_return']
    percentile = 100 * sum((x < actual) + .5 * (x == actual) for x in returns) / trials
    return dict(status='available', version=VERSION, symbol=symbol, seed=seed, trials=trials,
                target_trade_count=count, holding_period_days=holding,
                strategy_metrics=observed['metrics'], buy_and_hold=benchmark_payload,
                random=dict(status='available', samples=samples, strategy_percentile=percentile,
                            median_return=float(pd.Series(returns).median()),
                            p05_return=float(pd.Series(returns).quantile(.05)),
                            p95_return=float(pd.Series(returns).quantile(.95)),
                            matching_trade_count_trials=sum(s['trade_count']==count for s in samples)),
                limitations=[
                    '仅检验同一固定标的的历史择时表现，不能证明因果或未来有效性。',
                    '买入持有：首日收盘形成计划，次日开盘买入，最后一日开盘计划卖出；状态阻断时可能不成交或未平仓。',
                    '随机计划均匀抽取不重叠持仓窗口；同持有期、计划笔数匹配原策略已完成交易数，实际成交可能因资金、当日过滤或状态阻断而减少。',
                    '所有随机结果均保留，不按实际成交笔数筛选；请结合笔数匹配轮数和持仓比例解读。',
                    '历史百分位不是显著性检验；同一历史区间多次调参会产生选择偏差，仍需要样本外验证。',
                    '对照沿用本次数据复权及日频成交近似，未消除原始数据与模型限制。'])
