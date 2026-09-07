"""工作台策略目录：参数单位与默认值在此集中定义。"""
from copy import deepcopy
from .strategies.fixed import FixedAssetStrategy
from .strategies.rank import CrossSectionalRankStrategy


def _number(name, label, default, minimum, maximum, kind='integer', step=1):
    return dict(name=name, label=label, type=kind, default=default, min=minimum, max=maximum, step=step)


_REGISTRY = [
    dict(id='fixed_asset', constructor=FixedAssetStrategy, name='固定标的', description='全市场下跌家数触发后，下一交易日开盘买入指定标的。', version='1', parameters=[dict(name='symbol',label='标的代码',type='string',default='588000.SH')]),
    dict(id='cross_sectional_rank', constructor=CrossSectionalRankStrategy, name='横截面排名', description='触发后按动量、反转、波动率与成交量变化的标准分加权选股。窗口单位为交易日。', version='1', parameters=[
        dict(name='candidate_symbols',label='候选标的',type='array',default=['588000.SH','510300.SH','159915.SZ']),
        *[_number(n, label, default, 1, 252) for n,label,default in [('momentum_window','动量窗口',20),('reversal_window','反转窗口',3),('volatility_window','波动率窗口',20),('volume_window','成交量窗口',5)]],
        dict(name='weights',label='因子权重',type='object',default=dict(momentum=0.0,reversal=1.0,volatility=-0.25,volume=0.0)),
        _number('min_volume','最低成交量（原始数据单位）',0.0,0,1e15,'number',1)
    ])
]


def catalog():
    """返回可直接 JSON 序列化的策略目录副本。"""
    return deepcopy([{k:v for k,v in entry.items() if k != 'constructor'} for entry in _REGISTRY])


def build_strategy(strategy_id, parameters):
    """构造已注册策略；参数校验由工作台入口统一执行。"""
    for entry in _REGISTRY:
        if entry['id'] == strategy_id:
            return entry['constructor'](**parameters)
    raise ValueError('unknown strategy_id')
