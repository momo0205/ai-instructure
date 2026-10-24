"""退出规则只返回收盘意图；成交引擎仍独占现金、仓位与开盘撮合。"""
from dataclasses import dataclass
from copy import deepcopy

from strategy.indicators import simple_moving_average, SMA_METADATA
from strategy.validation import UserError, numeric

_CATALOG = [
    dict(id='fixed_holding', name='固定持有期', version='fixed-holding-v1',
         description='买入日 E 后第 H 个研究交易日开盘尝试卖出（E+H）。',
         parameters=[], supports_effectiveness=True, supports_studies=True),
    dict(id='close_below_sma', name='收盘低于均线', version='close-below-sma-v1',
         description='收盘价严格低于含当日的连续 N 日简单均线，次日开盘尝试卖出；最长持有期兜底。缺失行情不跳过，停牌日不产生新信号。',
         parameters=[dict(name='window', label='均线窗口（交易日）', type='integer', default=20, minimum=2, maximum=252),
                     dict(name='max_holding_days', label='最长持有交易日', type='integer', default=20, minimum=1, maximum=252)],
         supports_effectiveness=False, supports_studies=False, indicators=[SMA_METADATA]),
]


def exit_policy_catalog():
    return deepcopy(_CATALOG)


def normalize_exit_policy(value):
    """请求边界严格校验；固定期不复制旧 holding_period_days 参数。"""
    if value is None:
        return {'id': 'fixed_holding', 'parameters': {}}
    if not isinstance(value, dict) or set(value) - {'id', 'parameters'}:
        raise UserError('INVALID_REQUEST', 'exit_policy 必须是仅含 id、parameters 的对象')
    ident = value.get('id')
    item = next((p for p in _CATALOG if p['id'] == ident), None)
    if item is None:
        raise UserError('INVALID_REQUEST', '未知退出规则 exit_policy.id')
    parameters = value.get('parameters', {})
    allowed = {p['name'] for p in item['parameters']}
    if not isinstance(parameters, dict) or set(parameters) - allowed:
        raise UserError('INVALID_REQUEST', '退出规则 parameters 含未知参数或不是对象')
    normalized = {p['name']: numeric(parameters.get(p['name'], p['default']), p['name'],
                    p['minimum'], p['maximum'], integer=True) for p in item['parameters']}
    return {'id': ident, 'parameters': normalized}


@dataclass(frozen=True)
class ExitPolicy:
    id: str
    version: str
    holding_days: int
    window: int | None = None

    @property
    def scheduled_reason(self):
        return 'holding period' if self.id == 'fixed_holding' else 'max_holding_days'

    def evaluate_close(self, history, day, symbol, held_sessions, *, suspended=False):
        """调用方提供截至收盘的只读视图，信号最早在下一交易日撮合。"""
        event = dict(date=day, symbol=symbol, rule=self.id, version=self.version,
                     status='hold', reason='holding_period' if self.window is None else 'close_not_below_sma',
                     close=None, sma=None, window=self.window, available=None,
                     held_sessions=held_sessions, planned_exit_date=None, exit_signal_date=None)
        if self.window is None:
            return event
        value = simple_moving_average(history, symbol, day, self.window)
        rows = history[(history['date'] == day) & (history['symbol'] == symbol)]
        close = None if rows.empty else rows.iloc[0]['close']
        import math
        close = float(close) if close is not None and math.isfinite(float(close)) else None
        event.update(close=close, sma=value.value, available=value.available)
        if suspended:
            event.update(reason='suspended')
        elif value.value is None:
            event.update(status='indicator_unavailable', reason=value.reason)
        elif close < value.value:
            event.update(status='triggered', reason='close_below_sma', exit_signal_date=day)
        return event


def build_exit_policy(value, holding_period_days):
    normalized = normalize_exit_policy(value)
    item = next(p for p in _CATALOG if p['id'] == normalized['id'])
    parameters = normalized['parameters']
    return ExitPolicy(item['id'], item['version'], parameters.get('max_holding_days', holding_period_days),
                      parameters.get('window'))
