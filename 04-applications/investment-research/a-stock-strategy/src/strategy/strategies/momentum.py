"""价格动量规则适配；来源和与 Qlib 的差异见 docs/strategy-adapters.md。"""
import numpy as np
import pandas as pd
from strategy.domain import Selection
from strategy.validation import numeric


class MomentumStrategy:
    def __init__(self, candidate_symbols=None, lookback=20, minimum_momentum=0):
        self.candidate_symbols = list(candidate_symbols or [])
        self.lookback = numeric(lookback, 'lookback', 1, 252, True)
        self.minimum_momentum = numeric(minimum_momentum, 'minimum_momentum', -1, 100)

    def select(self, as_of, market, universe):
        if not market.triggered or universe.empty:
            return None
        frame = universe.copy()
        frame['date'] = pd.to_datetime(frame['date'])
        # 即使调用方传入全历史，也必须先截断未来，再取窗口。
        frame = frame[(frame.date.dt.date <= as_of) & frame.symbol.isin(self.candidate_symbols)]
        candidates = []
        for symbol, hist in frame.groupby('symbol', sort=True):
            if hist.date.dt.date.duplicated().any():
                continue
            hist = hist.sort_values('date').tail(self.lookback + 1)
            if len(hist) != self.lookback + 1 or hist.date.dt.date.duplicated().any():
                continue
            latest = hist.iloc[-1]
            if latest.date.date() != as_of:
                continue
            if any(bool(latest.get(flag, False)) for flag in ('is_suspended', 'limit_up', 'limit_down')):
                continue
            prices = pd.to_numeric(hist.close, errors='coerce').to_numpy(dtype=float)
            if not np.isfinite(prices).all() or (prices <= 0).any():
                continue
            # Qlib Alpha158 ROC 是过去价/当前价；倒数减一才是通常的区间收益。
            roc = float(prices[0] / prices[-1])
            momentum = float(prices[-1] / prices[0] - 1)
            if not np.isfinite(momentum) or momentum < self.minimum_momentum:
                continue
            candidates.append(Selection(str(symbol), momentum,
                {'as_of': as_of.isoformat(), 'momentum': momentum, 'qlib_roc': roc,
                 'lookback': self.lookback}, 'highest trailing price return above minimum'))
        # 固定同分规则，避免输入行顺序或候选列表顺序改变结果。
        return sorted(candidates, key=lambda item: (-item.score, item.symbol))[0] if candidates else None
