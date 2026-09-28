"""Qlib 提供预计算分数，本地引擎提供交易约束与成交。"""
import numpy as np
import pandas as pd
from strategy.domain import Selection
from strategy.strategies.momentum import MomentumStrategy
from strategy.strategies.decision_evidence import candidate, choose
from strategy.validation import UserError


class QlibMomentumStrategy(MomentumStrategy):
    def __init__(self, candidate_symbols=None, lookback=20, minimum_momentum=0):
        super().__init__(candidate_symbols,lookback,minimum_momentum)
        self.scores = {}
        self.factor_runtime = None
        self.prepared = False

    def prepare(self, market, output_dir):
        from strategy.adapters.qlib_factors import compute_factors
        rows, self.factor_runtime = compute_factors(market,self.candidate_symbols,self.lookback,output_dir)
        self.scores = {(row['date'],row['symbol']):row['score'] for row in rows}
        self.prepared = True
        return self

    def evaluate(self, as_of, market, universe):
        if not self.prepared:
            raise UserError('QLIB_FAILED', 'Qlib 因子尚未准备，请通过工作台或 CLI 请求入口执行。')
        if not market.triggered or universe.empty:
            return None, []
        frame = universe.copy()
        frame['date'] = pd.to_datetime(frame.date).dt.date
        frame = frame[frame.date <= as_of]
        sessions = sorted(frame.date.unique())[-self.lookback-1:]
        selections, evidence = [], []
        for symbol in sorted(set(self.candidate_symbols)):
            row = candidate(symbol)
            evidence.append(row)
            if len(sessions) != self.lookback + 1:
                continue
            rows = frame[(frame.symbol == symbol) & frame.date.isin(sessions)].sort_values('date')
            if rows.date.duplicated().any():
                row['reason'] = 'duplicate_dates'
                continue
            if len(rows) != len(sessions):
                continue
            if rows.iloc[-1].date != as_of:
                row['reason'] = 'missing_current_bar'
                continue
            prices = pd.to_numeric(rows.close,errors='coerce').to_numpy(dtype=float)
            if not np.isfinite(prices).all() or (prices <= 0).any():
                row['reason'] = 'invalid_price'
                continue
            blocked = next((flag for flag in ('is_suspended','limit_up','limit_down')
                            if bool(rows.iloc[-1].get(flag,False))), None)
            if blocked:
                row['reason'] = blocked
                continue
            row.update(reference_date=rows.iloc[0].date.isoformat(),
                       reference_close=float(prices[0]), current_close=float(prices[-1]))
            # 解释必须用 Qlib 实际输出，不能用本地重算的分数冒充。
            score = self.scores.get((as_of.isoformat(),symbol))
            if score is None:
                row['reason'] = 'missing_factor'
                continue
            row['score'] = score
            if score < self.minimum_momentum:
                row['reason'] = 'below_minimum'
                continue
            row['status'] = 'eligible'
            selections.append(Selection(symbol,score,{'as_of':as_of.isoformat(),'momentum':score,
                'lookback':self.lookback,'factor_backend':'qlib'},'highest Qlib momentum above minimum'))
        return choose(selections, evidence)
