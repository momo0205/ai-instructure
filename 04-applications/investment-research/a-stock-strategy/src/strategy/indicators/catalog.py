"""Trusted, categorized indicator definitions shared by analysis and the UI."""
from copy import deepcopy
import math
import re


def _window(default):
    return dict(name='window', label='窗口（交易日）', type='integer', default=default, min=2, max=252)


_CATALOG = [
    dict(id='ohlc', category='price', name='日线价格', description='所选来源的开、高、低、收；保留其复权口径。',
         kind='source', version='source-v1', formula='原始日线字段', inputs=['open','high','low','close'],
         outputs=[dict(name=k, unit='价格') for k in ('open','high','low','close')], parameters=[], warmup=0, panel='price'),
    dict(id='sma', category='trend', name='简单均线 SMA', description='连续 N 个有效收盘价的算术平均。',
         kind='derived', version='sma-v1', formula='sum(close[-N:]) / N', inputs=['close'],
         outputs=[dict(name='value', unit='价格')], parameters=[_window(20)], warmup='连续 N 日', panel='price'),
    dict(id='ema', category='trend', name='指数均线 EMA', description='首个连续 N 日的 SMA 作种子；缺口后重新播种。',
         kind='derived', version='ema-v1', formula='seed=SMA(N); EMA=2/(N+1)*close+(1-2/(N+1))*previous',
         inputs=['close'], outputs=[dict(name='value', unit='价格')], parameters=[_window(20)],
         warmup='连续 N 日作种子', panel='price'),
    dict(id='bollinger', category='volatility', name='布林带', description='中轨是 SMA；上下轨使用总体标准差。',
         kind='derived', version='bollinger-v1', formula='middle=SMA(N); upper/lower=middle±K*population_std(N)',
         inputs=['close'], outputs=[dict(name=k, unit='价格') for k in ('middle','upper','lower')],
         parameters=[_window(20),dict(name='multiplier',label='标准差倍数',type='number',default=2.0,min_exclusive=0,max=10)],
         warmup='连续 N 日', panel='price'),
    dict(id='volume', category='volume', name='成交量', description='所选来源的原始成交量，零值有效。',
         kind='source', version='source-v1', formula='原始日线字段', inputs=['volume'],
         outputs=[dict(name='volume', unit='来源声明单位')], parameters=[], warmup=0, panel='volume'),
    dict(id='amount', category='volume', name='成交额', description='所选来源的原始成交额。',
         kind='source', version='source-v1', formula='原始日线字段', inputs=['amount'],
         outputs=[dict(name='amount', unit='来源声明单位')], parameters=[], warmup=0, panel='volume'),
    dict(id='volume_sma', category='volume', name='成交量均线', description='连续 N 个有效成交量的算术平均。',
         kind='derived', version='volume-sma-v1', formula='sum(volume[-N:]) / N', inputs=['volume'],
         outputs=[dict(name='value', unit='来源声明成交量单位')], parameters=[_window(5)],
         warmup='连续 N 日', panel='volume'),
]


def indicator_catalog() -> list[dict]:
    """Return a mutable JSON copy; callers cannot alter trusted definitions."""
    return deepcopy(_CATALOG)


def normalize_instances(value: object) -> list[dict]:
    if not isinstance(value, list) or len(value) > 12:
        raise ValueError('indicators: expected at most 12 instances')
    definitions = {item['id']: item for item in _CATALOG if item['kind'] == 'derived'}
    seen = set()
    result = []
    for item in value:
        if not isinstance(item, dict) or set(item) - {'instance_id','id','parameters'}:
            raise ValueError('indicator instance: invalid fields')
        instance_id = item.get('instance_id')
        identifier = item.get('id')
        if not isinstance(instance_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,39}', instance_id) or instance_id in seen:
            raise ValueError('indicator instance_id: invalid or duplicate')
        if not isinstance(identifier, str) or identifier not in definitions:
            raise ValueError('indicator id: unknown derived indicator')
        given = item.get('parameters', {})
        schema = {p['name']: p for p in definitions[identifier]['parameters']}
        if not isinstance(given, dict) or set(given) - set(schema):
            raise ValueError('indicator parameters: unknown parameter')
        parameters = {}
        for name, field in schema.items():
            raw = given.get(name, field['default'])
            if field['type'] == 'integer':
                if isinstance(raw, bool) or not isinstance(raw, int) or not field['min'] <= raw <= field['max']:
                    raise ValueError(f'{name}: expected integer {field["min"]}–{field["max"]}')
                parameters[name] = raw
            else:
                if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not 0 < raw <= field['max']:
                    raise ValueError(f'{name}: expected finite number > 0 and <= {field["max"]}')
                parameters[name] = float(raw)
        seen.add(instance_id)
        result.append(dict(instance_id=instance_id, id=identifier, parameters=parameters))
    return result
