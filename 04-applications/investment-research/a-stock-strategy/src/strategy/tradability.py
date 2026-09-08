"""行情证据适配与成交资格规则；不负责联网，也不从全天量价推断开盘状态。"""
from dataclasses import dataclass
import math
from typing import Protocol

TRADABILITY_VERSION = 'daily-status-approximate-v1'


@dataclass(frozen=True)
class TradingStatus:
    has_row: bool
    valid_open: bool
    suspended: bool | None = None
    limit_up: bool | None = None
    limit_down: bool | None = None
    source: str = 'daily-bar-flags'


class StatusProvider(Protocol):
    """数据源先提供开盘时可知的证据，规则层不依赖具体下载接口。"""
    def read(self, row) -> TradingStatus: ...


class DailyBarStatusProvider:
    def __init__(self, *, flags_verified: bool = False):
        self.flags_verified = flags_verified

    def read(self, row) -> TradingStatus:
        if row is None:
            return TradingStatus(False, False)
        try:
            price = float(row['open'])
            valid = math.isfinite(price) and price > 0
        except (KeyError, TypeError, ValueError):
            valid = False

        def flag(key):
            value = row.get(key)
            # 现有下载器用 False 填充未知；不能将其升级为“已验证可交易”。
            text = str(value).strip().lower()
            if text in {'1', '1.0', 'true', 't', 'yes', 'y'}:
                return True
            if self.flags_verified and text in {'0', '0.0', 'false', 'f', 'no', 'n'}:
                return False
            return None

        return TradingStatus(True, valid, flag('is_suspended'), flag('limit_up'), flag('limit_down'))


def execution_block(status: TradingStatus, side: str, kind: str | None) -> str:
    """固定近似模式：未知状态允许估算；已知阻断返回原因，由引擎处理订单生命周期。"""
    if side not in {'buy', 'sell'}:
        raise ValueError('side must be buy or sell')
    if not status.has_row:
        return 'missing_row'
    if not status.valid_open:
        return 'invalid_open'
    if status.suspended is True:
        return 'suspended'
    if side == 'buy' and status.limit_up is True:
        return 'limit_up'
    if status.limit_down is True and (side == 'sell' or kind != 'stock'):
        return 'limit_down'
    return ''
