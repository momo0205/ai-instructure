from datetime import date

import pandas as pd

from strategy.domain import MarketState
from strategy.signals import MarketTrigger
from strategy.strategies.fixed import FixedAssetStrategy
from strategy.strategies.rank import CrossSectionalRankStrategy
from strategy.recommendation import recommend


def _market(triggered=True):
    return MarketState(date(2026, 8, 10), 4100, -0.01, triggered)


def test_market_trigger_requires_level_and_negative_return():
    trigger = MarketTrigger(trigger_level=4000)
    assert trigger.evaluate(4001, -0.01, date(2026,8,10)).triggered
    assert not trigger.evaluate(3999, -0.01, date(2026,8,10)).triggered
    assert not trigger.evaluate(4001, 0.01, date(2026,8,10)).triggered

def test_market_trigger_requires_explicit_as_of():
    import pytest
    with pytest.raises(ValueError):
        MarketTrigger().evaluate(4001, -0.01)


def test_fixed_asset_selection():
    frame = pd.DataFrame([{"date": date(2026, 8, 10), "symbol": "588000.SH", "close": 1.0}])
    result = FixedAssetStrategy("588000.SH").select(date(2026, 8, 10), _market(), frame)
    assert result and result.symbol == "588000.SH"

def test_fixed_requires_exact_as_of_and_rank_requires_trigger():
    frame = pd.DataFrame([{"date": date(2026, 8, 9), "symbol": "588000.SH", "close": 1.0}])
    assert FixedAssetStrategy("588000.SH").select(date(2026, 8, 10), _market(), frame) is None
    assert CrossSectionalRankStrategy(candidate_symbols=["AAA"]).select(date(2026, 8, 10), _market(False), frame) is None


def test_rank_uses_only_history_and_filters_untradable():
    rows = []
    for d, a, b in [(date(2026,8,8),10,10),(date(2026,8,9),11,11),(date(2026,8,10),12,13),(date(2026,8,11),100,1)]:
        rows.extend([
            {"date": d, "symbol": "AAA", "close": a, "volume": 100, "is_suspended": False, "limit_up": False, "limit_down": False},
            {"date": d, "symbol": "BBB", "close": b, "volume": 100, "is_suspended": False, "limit_up": d == date(2026,8,10), "limit_down": False},
        ])
    result = CrossSectionalRankStrategy(candidate_symbols=["AAA", "BBB"], momentum_window=2, reversal_window=1, volatility_window=1, volume_window=1).select(date(2026,8,10), _market(), pd.DataFrame(rows))
    assert result and result.symbol == "AAA"
    assert result.features["as_of"] == "2026-08-10"


def test_rank_empty_selection():
    frame = pd.DataFrame([{"date": date(2026,8,10), "symbol":"AAA", "close":1, "is_suspended":True, "limit_up":False, "limit_down":False}])
    assert CrossSectionalRankStrategy(candidate_symbols=["AAA"]).select(date(2026,8,10), _market(), frame) is None


def test_rank_excludes_zero_prior_volume_with_explicit_reason_and_finite_features():
    rows = []
    for d, close, volume in [(date(2026, 8, 8), 10, 100), (date(2026, 8, 9), 11, 0),
                             (date(2026, 8, 10), 12, 100)]:
        rows.append({"date": d, "symbol": "AAA", "close": close, "volume": volume,
                     "is_suspended": False, "limit_up": False, "limit_down": False})
        rows.append({"date": d, "symbol": "000001.SH", "close": 4100 if d != date(2026, 8, 10) else 4000,
                     "volume": 100, "is_suspended": False, "limit_up": False, "limit_down": False})
    strategy = CrossSectionalRankStrategy(candidate_symbols=["AAA"], momentum_window=1,
                                          reversal_window=1, volatility_window=1, volume_window=1)
    result = recommend(date(2026, 8, 10), pd.DataFrame(rows), strategy)
    assert result.selected is None
    assert any(item["symbol"] == "AAA" and "volume" in item["reason"] for item in result.filtered)
    assert all(pd.notna(item.get("score", 0)) for item in result.rankings)
