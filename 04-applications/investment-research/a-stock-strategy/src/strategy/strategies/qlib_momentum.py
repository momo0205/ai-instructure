"""Qlib 提供预计算分数，本地引擎提供交易约束与成交。"""
import numpy as np
import pandas as pd
from strategy.domain import Selection
from strategy.strategies.momentum import MomentumStrategy
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

    def select(self, as_of, market, universe):
        if not self.prepared:
            raise UserError('QLIB_FAILED', 'Qlib 因子尚未准备，请通过工作台或 CLI 请求入口执行。')
        if not market.triggered or universe.empty:
            return None
        frame = universe.copy()
        frame['date'] = pd.to_datetime(frame.date).dt.date
        frame = frame[frame.date<=as_of]
        sessions = sorted(frame.date.unique())[-self.lookback-1:]
        if len(sessions)!=self.lookback+1:
            return None
        selections=[]
        for symbol in sorted(self.candidate_symbols):
            score=self.scores.get((as_of.isoformat(),symbol))
            if score is None or score<self.minimum_momentum:
                continue
            rows=frame[(frame.symbol==symbol)&frame.date.isin(sessions)].sort_values('date')
            if len(rows)!=len(sessions) or rows.date.duplicated().any() or rows.iloc[-1].date!=as_of:
                continue
            prices=pd.to_numeric(rows.close,errors='coerce').to_numpy(dtype=float)
            if not np.isfinite(prices).all() or (prices<=0).any():
                continue
            if any(bool(rows.iloc[-1].get(flag,False)) for flag in ('is_suspended','limit_up','limit_down')):
                continue
            selections.append(Selection(symbol,score,{'as_of':as_of.isoformat(),'momentum':score,
                'lookback':self.lookback,'factor_backend':'qlib'},'highest Qlib momentum above minimum'))
        return sorted(selections,key=lambda item:(-item.score,item.symbol))[0] if selections else None
