"""择股与解释共用的轻量证据结构，不重新计算交易或未来收益。"""


def candidate(symbol):
    return dict(symbol=str(symbol), score=None, reference_date=None,
                reference_close=None, current_close=None, status='excluded', reason='insufficient_history')


def choose(selections, evidence):
    """一次排序同时产生赢家与落选原因；同分规则必须与实际选股一致。"""
    ranked = sorted(selections, key=lambda item: (-item.score, item.symbol))
    winner = ranked[0] if ranked else None
    for row in evidence:
        if row['status'] != 'eligible':
            continue
        if row['symbol'] == winner.symbol:
            row.update(status='selected', reason='selected')
        else:
            row['reason'] = 'tie_break' if row['score'] == winner.score else 'lower_score'
    return winner, evidence
