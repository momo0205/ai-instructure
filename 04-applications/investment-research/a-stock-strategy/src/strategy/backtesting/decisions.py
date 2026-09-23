"""收盘决策审计。只在引擎原有决策点运行，不事后重新模拟策略。"""
import math


def close_decision(strategy, day, market, history, position, next_day, market_warning=None):
    """返回真实选股与展示证据；持仓日不计算假想候选或触发新订单。"""
    record = dict(date=day, market_triggered=market.triggered,
                  declining_count=market.declining_count,
                  index_return_1d=market.index_return_1d if market.index_level > 0 and math.isfinite(market.index_return_1d) else None,
                  market_warning=market_warning,
                  position_symbol=position['symbol'] if position else None,
                  selected_symbol=None, planned_entry_date=None, candidates=[],
                  candidate_details_supported=False)
    if position is not None:
        record['status'] = 'holding'
        return None, record
    if callable(getattr(strategy, 'select_with_evidence', None)):
        selection, record['candidates'], record['candidate_details_supported'] = strategy.select_with_evidence(day, market, history)
    else:
        # 保留扩展策略的 select 合同；不在引擎强加额外市场门槛。
        selection = strategy.select(day, market, history)
    if selection is None:
        record['status'] = ('market_data_unavailable' if market_warning else
                            'no_candidate' if market.triggered else 'market_not_triggered')
    else:
        record.update(selected_symbol=selection.symbol, planned_entry_date=next_day,
                      status='selected' if next_day else 'no_next_session')
    return selection, record
