"""面向用户的稳定诊断契约；不依赖供应商英文日志，也不泄露未知异常原文。"""
import json
from collections import Counter
from strategy.validation import UserError

CATALOG = {
    'DATA_COVERAGE_INCOMPLETE': ('数据覆盖不完整', '选择共同覆盖的日期范围，或重新下载缺失行情。'),
    'DATA_VALIDATION_FAILED': ('行情数据验证失败', '重新下载数据；若仍失败，请提供任务编号检查来源及复权方式。'),
    'SYMBOL_NOT_CONFIRMED': ('数据源未确认证券代码', '检查代码，或稍后重试数据源查询。'),
    'INVALID_SYMBOL': ('证券代码不合法', '检查六位代码及 SH/SZ 交易所后缀。'),
    'INTERNAL_ERROR': ('服务处理请求失败', '请重试；若仍失败，请提供操作时间和任务编号。'),
    'INVALID_REQUEST': ('请求参数不合法', '检查标的、日期范围和策略参数后重新提交。'),
    'NOT_FOUND': ('请求的任务或资源不存在', '刷新页面后重新选择。'),
    'DOWNLOAD_FAILED': ('行情下载失败', '检查数据源连接及下载范围后重试。'),
    'BACKTEST_FAILED': ('回测执行失败', '检查数据完整性和参数；若仍失败，请提供任务编号。'),
    'TASK_INTERRUPTED': ('任务被服务中断', '服务恢复后重新提交任务。'),
    'INSUFFICIENT_CASH': ('买入资金不足', '初始资金须覆盖最小买入数量及费用；股票按 100 股整手买入，可调整模拟资金重跑。'),
    'ORDER_BLOCKED': ('部分订单被阻断', '查看成交、取消与延后记录，核对行情及交易状态。'),
    'OPEN_POSITION': ('已买入但尚未完成卖出', '查看期末持仓和卖出延后记录；胜率仅按已完成交易计算。'),
    'NO_COMPLETED_TRADES': ('本次没有完成交易', '检查触发条件、数据预热与成交取消记录，不能据此判断策略有效性。'),
    'RESEARCH_LIMITATIONS': ('结果存在数据或模型限制', '展开数据与模型说明，确认近似假设后再解读结果。'),
}


def diagnostic(code, *, message=None, context=None, severity='error'):
    title, action = CATALOG[code]
    return dict(code=code, severity=severity, message=message or title, action=action, context=context or {})


def exception_diagnostic(error, stage):
    if isinstance(error, UserError):
        return diagnostic(error.code, message=str(error), context=error.context)
    # 只按已知异常类型分类；第三方异常文本可能带路径或令牌。
    return diagnostic('INVALID_REQUEST' if stage == 'request' else
                      'DOWNLOAD_FAILED' if stage == 'download' else 'BACKTEST_FAILED')


def encode_error(item):
    """复用既有 TEXT 字段；版本标记避免将历史错误文本误当结构化诊断。"""
    return json.dumps({'diagnostic_version':1, 'diagnostic':item}, ensure_ascii=False)


def task_view(task, stage):
    value = dict(task)
    if value.get('error'):
        try:
            stored = json.loads(value['error'])
        except (ValueError, TypeError):
            stored = None
        if isinstance(stored, dict) and stored.get('diagnostic_version') == 1:
            item = stored['diagnostic']
        else:
            item = diagnostic('TASK_INTERRUPTED' if value['status'] == 'interrupted' else
                              'DOWNLOAD_FAILED' if stage == 'download' else 'BACKTEST_FAILED')
        value.update(error=item['message'], diagnostic=item)
    if value.get('result') is not None:
        value['result'] = dict(value['result'])
        value['result'].setdefault('diagnostics', result_diagnostics(value['result']))
    return value


def result_diagnostics(result):
    items = []
    events = result.get('execution_events', [])
    entries = [e for e in events if e['side'] == 'buy']
    filled = sum(e['status'] == 'filled' for e in entries)
    exits = sum(e['side'] == 'sell' and e['status'] == 'filled' for e in events)
    # 引擎当前只持有单个仓位；买入成交数超过卖出成交数代表期末持仓。
    if filled > exits:
        items.append(diagnostic('OPEN_POSITION', severity='warning',
                                message='期末仍有未平仓头寸；已完成交易指标不包含该头寸的胜负'))
    blocked = [e for e in entries if e['status'] == 'cancelled' and e.get('reason') == 'insufficient_cash']
    if blocked:
        required = [e['required_cash'] for e in blocked if e.get('required_cash') is not None]
        context = dict(count=len(blocked))
        if required:
            context.update(minimum_required_cash=min(required), maximum_required_cash=max(required),
                           available_cash=blocked[0].get('cash'))
        suffix = '，本次没有买入成交' if not filled else '，部分买入未执行'
        items.append(diagnostic('INSUFFICIENT_CASH', severity='warning',
                                message=f'{len(blocked)} 次买入因资金不足取消{suffix}', context=context))
    reasons = Counter(e.get('reason', 'unknown') for e in events
                      if e['status'] in ('cancelled', 'deferred') and e.get('reason') != 'insufficient_cash')
    if reasons:
        labels = {'missing_row':'缺少行情', 'invalid_open':'开盘价无效', 'suspended':'停牌',
                  'limit_up':'涨停限制', 'limit_down':'跌停限制'}
        message = '订单取消或延后：' + '；'.join(f'{labels.get(reason, "其他执行限制")} {count} 次' for reason, count in reasons.items())
        items.append(diagnostic('ORDER_BLOCKED', severity='warning', message=message, context=dict(counts=dict(reasons))))
    if not result.get('trades') and not items:
        items.append(diagnostic('NO_COMPLETED_TRADES', severity='warning'))
    if result.get('warnings'):
        items.append(diagnostic('RESEARCH_LIMITATIONS', severity='warning'))
    return items


def error_response(item):
    return {'error':item['message'], 'diagnostic':item}
