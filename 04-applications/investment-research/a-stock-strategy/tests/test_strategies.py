from datetime import date

import pandas as pd

from strategy.domain import MarketState
from strategy.signals import MarketTrigger
from strategy.strategies.fixed import FixedAssetStrategy
from strategy.strategies.rank import CrossSectionalRankStrategy


def _market(triggered=True):
    return MarketState(date(2026, 8, 10), 4100, -0.01, triggered)


def test_market_trigger_requires_level_and_negative_return():
    trigger = MarketTrigger(trigger_level=4000)
    assert trigger.evaluate(4001, -0.01).triggered
    assert not trigger.evaluate(3999, -0.01).triggered
    assert not trigger.evaluate(4001, 0.01).triggered


def test_fixed_asset_selection():
    frame = pd.DataFrame([{"date": date(2026, 8, 10), "symbol": "588000.SH", "close": 1.0}])
    result = FixedAssetStrategy("588000.SH").select(date(2026, 8, 10), _market(), frame)
    assert result and result.symbol == "588000.SH"


def test_rank_uses_only_history_and_filters_untradable():
    rows = []
    for d, a, b in [(date(2026,8,8),10,10),(date(2026,8,9),11,11),(date(2026,8,10),12,13),(date(2026,8,11),100,1)]:
        rows.extend([
            {"date": d, "symbol": "AAA", "close": a, "volume": 100, "is_suspended": False, "limit_up": False, "limit_down": False},
            {"date": d, "symbol": "BBB", "close": b, "volume": 100, "is_suspended": False, "limit_up": d == date(2026,8,10), "limit_down": False},
        ])
    result = CrossSectionalRankStrategy(candidate_symbols=["AAA", "BBB"], momentum_window=2, reversal_window=1).select(date(2026,8,10), _market(), pd.DataFrame(rows))
    assert result and result.symbol == "AAA"
    assert result.features["as_of"] == "2026-08-10"


def test_rank_empty_selection():
    frame = pd.DataFrame([{"date": date(2026,8,10), "symbol":"AAA", "close":1, "is_suspended":True, "limit_up":False, "limit_down":False}])
    assert CrossSectionalRankStrategy(candidate_symbols=["AAA"]).select(date(2026,8,10), _market(), frame) is None
