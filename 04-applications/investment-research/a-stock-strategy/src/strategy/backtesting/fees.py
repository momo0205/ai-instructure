"""现金证券费用规则；撮合和预算共用相同规则，避免费率散落在引擎中。"""
from dataclasses import asdict, dataclass
from datetime import date
import math

FEES_VERSION = 'cn-cash-equity-fees-v1'
STOCK_SUPPORTED_FROM = date(2022, 7, 1)
STOCK_BUY_LOT_SIZE = 100


@dataclass(frozen=True, slots=True)
class StockFeePeriod:
    effective_from: date
    sell_stamp_duty_rate: float
    transfer_fee_rate: float


# 当前范围仅覆盖过户费调整后的日期；印花税按实际卖出日选择。
# 原印花税：https://tianjin.chinatax.gov.cn/11200000000/0300/030005/20220725150235434.shtml
# 减半：https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20230827_5725662.shtml
# 双边过户费：https://one.sse.com.cn/onething/gptz/
STOCK_FEE_SCHEDULE = (
    StockFeePeriod(STOCK_SUPPORTED_FROM, .001, .00001),
    StockFeePeriod(date(2023, 8, 28), .0005, .00001),
)


@dataclass(frozen=True, slots=True)
class FeeBreakdown:
    commission: float = 0.0
    stamp_duty: float = 0.0
    transfer_fee: float = 0.0

    @property
    def total(self) -> float:
        return self.commission + self.stamp_duty + self.transfer_fee


@dataclass(frozen=True, slots=True)
class FeeRules:
    commission_rate: float
    minimum_commission: float
    legacy_stamp_duty_rate: float = .001

    def __post_init__(self):
        if any(not math.isfinite(value) or value < 0 for value in (
                self.commission_rate, self.minimum_commission, self.legacy_stamp_duty_rate)):
            raise ValueError('fee parameters must be finite and non-negative')

    def validate_instrument(self, kind: str | None, day: date) -> None:
        if kind not in (None, 'stock', 'etf'):
            raise ValueError('unsupported instrument type')
        if kind == 'stock' and day < STOCK_SUPPORTED_FROM:
            raise ValueError(f'stock trading rules support dates from {STOCK_SUPPORTED_FROM}')

    def _rates(self, day, kind, side):
        self.validate_instrument(kind, day)
        if side not in ('buy', 'sell'):
            raise ValueError('side must be buy or sell')
        if kind == 'stock':
            period = next(row for row in reversed(STOCK_FEE_SCHEDULE) if day >= row.effective_from)
            return (period.sell_stamp_duty_rate if side == 'sell' else 0.0, period.transfer_fee_rate)
        return (self.legacy_stamp_duty_rate if kind is None and side == 'sell' else 0.0, 0.0)

    def commission(self, notional: float) -> float:
        return max(self.minimum_commission, notional * self.commission_rate) if notional else 0.0

    def calculate(self, notional: float, day: date, kind: str | None, side: str) -> FeeBreakdown:
        if not math.isfinite(notional) or notional < 0:
            raise ValueError('notional must be finite and non-negative')
        stamp, transfer = self._rates(day, kind, side)
        return FeeBreakdown(self.commission(notional), notional * stamp, notional * transfer)

    def quantity(self, cash: float, price: float, day: date, kind: str | None, lot_size: int) -> float:
        stamp, transfer = self._rates(day, kind, 'buy')
        if price <= 0 or cash <= self.minimum_commission:
            return 0.0
        lot = STOCK_BUY_LOT_SIZE if kind == 'stock' else lot_size
        if not lot:
            # 兼容旧连续份额算法，避免改变历史 ETF/未分类调用结果。
            return max(0.0, (cash - self.minimum_commission) / (price * (1 + self.commission_rate)))
        affordable = min(cash / (1 + self.commission_rate + stamp + transfer),
                         (cash - self.minimum_commission) / (1 + stamp + transfer)) / price
        quantity = max(0, math.floor(affordable / lot)) * lot
        if kind == 'stock':
            # 以实际费用复核浮点边界，防止整手下单后现金出现微小负数。
            while quantity and quantity * price + self.calculate(quantity * price, day, kind, 'buy').total > cash:
                quantity -= lot
        return quantity

    def metadata(self) -> dict:
        return dict(version=FEES_VERSION, stock_supported_from=STOCK_SUPPORTED_FROM.isoformat(),
                    stock_buy_lot_size=STOCK_BUY_LOT_SIZE,
                    commission={'rate': self.commission_rate, 'minimum': self.minimum_commission,
                                'includes_exchange_levies': True},
                    stock_schedule=[asdict(row) | {'effective_from': row.effective_from.isoformat()}
                                    for row in STOCK_FEE_SCHEDULE],
                    stock_stamp_duty_side='sell', stock_transfer_fee_side='both',
                    etf={'stamp_duty_rate': 0.0, 'transfer_fee_rate': 0.0},
                    legacy_stamp_duty_rate=self.legacy_stamp_duty_rate)
