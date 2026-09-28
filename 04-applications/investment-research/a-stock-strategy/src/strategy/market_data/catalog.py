"""纯证券目录：代码校验和回测支持范围判断，不请求行情。"""
import re
from strategy.validation import UserError

from strategy.backtesting.fees import STOCK_SUPPORTED_FROM

VERIFIED_ETFS = {'588000.SH':'科创50ETF', '510300.SH':'沪深300ETF', '159915.SZ':'创业板ETF'}


def validate_symbol(symbol):
    """显式交易所避免把深市股票误当上证证券，不自动修改用户输入。"""
    if not isinstance(symbol, str) or not re.fullmatch(r'\d{6}\.(SH|SZ)', symbol):
        raise UserError('INVALID_SYMBOL', '代码格式应为 588000.SH 或 002015.SZ')
    code, exchange = symbol.split('.')
    expected = 'SH' if code[0] in '56' else 'SZ' if code[0] in '013' else None
    if expected is None:
        raise UserError('INVALID_SYMBOL', '当前下载仅支持沪深股票及基金代码')
    if exchange != expected:
        raise UserError('INVALID_SYMBOL', f'交易所不匹配，请使用 {code}.{expected}')
    return symbol


def describe(symbol, metadata=None):
    metadata = metadata or {}
    kind = 'etf' if symbol in VERIFIED_ETFS else 'index' if symbol == '000001.SH' else metadata.get('kind', 'stock' if re.fullmatch(r'(?:[036]\d{5})\.(?:SZ|SH)', symbol) else 'unknown')
    # 代码范围和已识别元数据同时满足才开放股票。当前名称不能替代历史 ST 状态。
    stock_name = metadata.get('name', '')
    mainboard = bool(re.fullmatch(r'(?:(?:000|001|002|003)\d{3}\.SZ|(?:600|601|603|605)\d{3}\.SH)',symbol))
    stock_supported = (mainboard and kind == 'stock' and metadata.get('kind') == 'stock'
                       and isinstance(stock_name,str) and bool(stock_name.strip())
                       and 'ST' not in stock_name.upper() and '退' not in stock_name)
    supported = symbol in VERIFIED_ETFS or stock_supported
    return dict(symbol=symbol, name=VERIFIED_ETFS.get(symbol, '上证指数' if symbol=='000001.SH' else metadata.get('name', symbol)),
                kind=kind, backtest_supported=supported, execution_mode='approximate',
                backtest_start=STOCK_SUPPORTED_FROM.isoformat() if stock_supported else None,
                reason='普通主板股票：日频近似回测，历史交易状态未完整验证' if stock_supported else
                    '' if supported else '尚未支持该证券的交易规则或未识别完整元数据；仅提供行情')
