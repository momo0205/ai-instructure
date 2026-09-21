"""显式策略扩展合同：参数、标的、预热和构造属于策略定义。"""
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable

from strategy.strategies.fixed import FixedAssetStrategy
from strategy.strategies.rank import CrossSectionalRankStrategy
from strategy.strategies.momentum import MomentumStrategy
from strategy.strategies.qlib_momentum import QlibMomentumStrategy
from strategy.validation import numeric


@dataclass
class StrategyDefinition:
    """注册启动时可信 Python 定义；回调接收已归一化参数。

    复杂参数可覆写 normalize_parameters；symbols 返回所需交易标的列表，
    warmup_sessions 返回每个标的需要的区间前交易日数。
    """
    id: str
    name: str
    description: str
    version: str
    parameters: list[dict]
    constructor: Callable
    symbol_selector: Callable
    warmup: Callable = lambda parameters: 0
    provenance: dict | None = None
    prepare: Callable = lambda strategy, market, output_dir: strategy

    def normalize_parameters(self, parameters):
        schema = {p['name']: p for p in self.parameters}
        if not isinstance(parameters, dict) or set(parameters)-set(schema):
            raise ValueError('unknown strategy parameters')
        result = deepcopy({key: p['default'] for key, p in schema.items()} | parameters)
        for key, parameter in schema.items():
            if parameter['type'] in ('number', 'integer'):
                result[key] = numeric(result[key], key, parameter['min'], parameter['max'], parameter['type']=='integer')
            else:
                expected = {'string': str, 'array': list, 'object': dict, 'boolean': bool}.get(parameter['type'])
                if expected is None:
                    raise ValueError(f"{key}: unsupported parameter type {parameter['type']}")
                if not isinstance(result[key], expected):
                    raise ValueError(f"{key}: expected {parameter['type']}")
            # Choice constraints are enforced on the server even for direct API callers.
            for attribute in ('options', 'enum'):
                if attribute in parameter and result[key] not in parameter[attribute]:
                    raise ValueError(f"{key}: expected one of {parameter[attribute]}")
        return result

    def symbols(self, parameters):
        return self.symbol_selector(parameters)

    def warmup_sessions(self, parameters):
        sessions = self.warmup(parameters)
        if isinstance(sessions, bool) or not isinstance(sessions, int) or sessions < 0:
            raise ValueError('warmup: expected non-negative integer sessions')
        return sessions

    def build(self, parameters):
        return self.constructor(**parameters)

    def catalog_entry(self):
        result = dict(id=self.id, name=self.name, description=self.description,
                      version=self.version, parameters=self.parameters)
        if self.provenance:
            result['provenance'] = self.provenance
        return deepcopy(result)


class RankStrategyDefinition(StrategyDefinition):
    def normalize_parameters(self, parameters):
        result = super().normalize_parameters(parameters)
        defaults = next(p['default'] for p in self.parameters if p['name']=='weights')
        weights = result['weights']
        if not isinstance(weights, dict) or set(weights)-set(defaults):
            raise ValueError('unknown weights')
        result['weights'] = deepcopy(defaults) | {k: numeric(v, 'weights', -100, 100) for k, v in weights.items()}
        return result


_REGISTRY = {}


def register_strategy(definition):
    """显式注册，拒绝覆盖已有策略。"""
    if definition.id in _REGISTRY:
        raise ValueError(f'strategy already registered: {definition.id}')
    _REGISTRY[definition.id] = definition


def get_strategy_definition(strategy_id):
    if not isinstance(strategy_id, str) or strategy_id not in _REGISTRY:
        raise ValueError('unknown strategy_id')
    return _REGISTRY[strategy_id]


def catalog():
    """返回可直接 JSON 序列化的策略目录副本。"""
    return [definition.catalog_entry() for definition in _REGISTRY.values()]


def build_strategy(strategy_id, parameters):
    """兼容已有构造入口；调用方应先通过定义归一化参数。"""
    return get_strategy_definition(strategy_id).build(parameters)


def _number(name, label, default, minimum, maximum, kind='integer', step=1):
    return dict(name=name, label=label, type=kind, default=default, min=minimum, max=maximum, step=step)


_BUILTINS = [
    dict(id='fixed_asset', constructor=FixedAssetStrategy, name='固定标的', description='全市场下跌家数触发后，下一交易日开盘买入指定标的。', version='1', parameters=[dict(name='symbol',label='标的代码',type='string',role='instrument',default='588000.SH')]),
    dict(id='cross_sectional_rank', constructor=CrossSectionalRankStrategy, name='横截面排名', description='触发后按动量、反转、波动率与成交量变化的标准分加权选股。窗口单位为交易日。', version='1', parameters=[
        dict(name='candidate_symbols',label='候选标的',type='array',role='instrument',default=['588000.SH','510300.SH','159915.SZ']),
        *[_number(n, label, default, 1, 252) for n,label,default in [('momentum_window','动量窗口',20),('reversal_window','反转窗口',3),('volatility_window','波动率窗口',20),('volume_window','成交量窗口',5)]],
        dict(name='weights',label='因子权重',type='object',default=dict(momentum=0.0,reversal=1.0,volatility=-0.25,volume=0.0)),
        _number('min_volume','最低成交量（原始数据单位）',0.0,0,1e15,'number',1)
    ])
]


register_strategy(StrategyDefinition(**_BUILTINS[0], symbol_selector=lambda p: [p['symbol']]))
register_strategy(RankStrategyDefinition(
    **_BUILTINS[1], symbol_selector=lambda p: p['candidate_symbols'],
    warmup=lambda p: max(p[k] for k in ('momentum_window', 'reversal_window', 'volatility_window', 'volume_window')),
))

register_strategy(StrategyDefinition(
    id='price_momentum', name='动量择强（价格规则适配）', version='1',
    description='市场条件触发后，按过去 N 个交易日涨幅选一只达到门槛的标的。参考 Qlib v0.9.7 ROC 因子，独立实现；非 Qlib 引擎或完整轮动策略。沿用下一日开盘及固定持有期。',
    constructor=MomentumStrategy,
    parameters=[
        dict(name='candidate_symbols', label='候选标的', type='array', role='instrument', default=['588000.SH','510300.SH','159915.SZ']),
        _number('lookback', '动量回看交易日', 20, 1, 252),
        _number('minimum_momentum', '最低动量（小数，0.05 表示 5%）', 0, -1, 100, 'number', .01),
    ],
    symbol_selector=lambda p: p['candidate_symbols'], warmup=lambda p: p['lookback'],
    provenance=dict(reference_project='Qlib', reference_version='v0.9.7',
        url='https://github.com/microsoft/qlib/blob/v0.9.7/qlib/contrib/data/loader.py',
        reference_license='MIT', integration='independent mathematical rule adaptation; no Qlib runtime',
        formula='momentum = 1 / Alpha158 ROC(N) - 1',
        execution='local market trigger, top 1, next open, fixed holding period'),
))

register_strategy(StrategyDefinition(
    id='qlib_momentum', name='Qlib 动量择强（独立因子引擎）', version='1',
    description='实际调用 Qlib 0.9.7 计算价格动量；市场触发、次日开盘与持有期由本系统执行。需要独立 Qlib 环境，窗口行情缺失则跳过。首次计算会增加运行时间。',
    constructor=QlibMomentumStrategy,
    parameters=deepcopy(get_strategy_definition('price_momentum').parameters),
    symbol_selector=lambda p:p['candidate_symbols'], warmup=lambda p:p['lookback'],
    prepare=lambda strategy,market,output_dir:strategy.prepare(market,output_dir),
    provenance=dict(reference_project='Qlib',reference_version='v0.9.7',reference_license='MIT',
        url='https://qlib.readthedocs.io/en/latest/component/data.html',
        integration='Qlib D.features in isolated worker; local execution engine',
        formula='$close/Ref($close, N)-1'),
))
