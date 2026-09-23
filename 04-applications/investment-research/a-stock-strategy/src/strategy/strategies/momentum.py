"""价格动量规则适配；来源和与 Qlib 的差异见 docs/strategy-adapters.md。"""
import numpy as np
import pandas as pd
from strategy.domain import Selection
from strategy.strategies.decision_evidence import candidate, choose
from strategy.validation import numeric


class MomentumStrategy:
    def __init__(self, candidate_symbols=None, lookback=20, minimum_momentum=0):
        self.candidate_symbols = list(candidate_symbols or [])
        self.lookback = numeric(lookback, 'lookback', 1, 252, True)
        self.minimum_momentum = numeric(minimum_momentum, 'minimum_momentum', -1, 100)

    def select(self, as_of, market, universe):
        # 外部兼容入口与审计入口使用同一次评估逻辑，避免解释和订单分叉。
        self._decision_evidence = self.evaluate(as_of, market, universe)
        return self._decision_evidence[0]

    def select_with_evidence(self, as_of, market, universe):
        """尊重扩展类的 select 覆盖；它改变了选择时，不冒充原动量解释。"""
        self._decision_evidence = None
        selection = self.select(as_of, market, universe)
        evidence = self._decision_evidence
        if evidence is None or evidence[0] != selection:
            return selection, [], False
        return selection, evidence[1], True

    def evaluate(self, as_of, market, universe):
        if not market.triggered or universe.empty:
            return None, []
        frame = universe.copy()
        frame['date'] = pd.to_datetime(frame['date'])
        # 即使调用方传入全历史，也必须先截断未来，再取窗口。
        frame = frame[(frame.date.dt.date <= as_of) & frame.symbol.isin(self.candidate_symbols)]
        selections, evidence = [], []
        for symbol in sorted(set(self.candidate_symbols)):
            row = candidate(symbol)
            evidence.append(row)
            hist = frame[frame.symbol == symbol]
            if hist.date.dt.date.duplicated().any():
                row['reason'] = 'duplicate_dates'
                continue
            hist = hist.sort_values('date').tail(self.lookback + 1)
            if len(hist) != self.lookback + 1:
                continue
            latest = hist.iloc[-1]
            if latest.date.date() != as_of:
                row['reason'] = 'missing_current_bar'
                continue
            blocked = next((flag for flag in ('is_suspended', 'limit_up', 'limit_down')
                            if bool(latest.get(flag, False))), None)
            if blocked:
                row['reason'] = blocked
                continue
            prices = pd.to_numeric(hist.close, errors='coerce').to_numpy(dtype=float)
            if not np.isfinite(prices).all() or (prices <= 0).any():
                row['reason'] = 'invalid_price'
                continue
            # 保留原有窗口与浮点运算，增加留痕不会改变历史择股。
            roc = float(prices[0] / prices[-1])
            momentum = float(prices[-1] / prices[0] - 1)
            row.update(reference_date=hist.iloc[0].date.date().isoformat(),
                       reference_close=float(prices[0]), current_close=float(prices[-1]))
            if not np.isfinite(momentum):
                row['reason'] = 'invalid_price'
                continue
            row['score'] = momentum
            if momentum < self.minimum_momentum:
                row['reason'] = 'below_minimum'
                continue
            row['status'] = 'eligible'
            selections.append(Selection(str(symbol), momentum,
                {'as_of': as_of.isoformat(), 'momentum': momentum, 'qlib_roc': roc,
                 'lookback': self.lookback}, 'highest trailing price return above minimum'))
        return choose(selections, evidence)
