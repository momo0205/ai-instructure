from datetime import date
import pandas as pd
import pytest

from strategy.backtest import BacktestEngine
from strategy.signals import MarketTrigger
from strategy.strategies.fixed import FixedAssetStrategy
from strategy.recommendation import recommend


def sample():
    rows = []
    for day, index, count, price in [("2024-01-02", 3300, 1000, 1),
                                     ("2024-01-03", 3267, 4000, .98),
                                     ("2024-01-04", 3300, 900, 1.00),
                                     ("2024-01-05", 3310, 800, 1.10)]:
        for symbol, close in [("000001.SH", index), ("588000.SH", price)]:
            rows.append(dict(date=day, symbol=symbol, open=close, high=close, low=close,
                             close=close, volume=10000, amount=10000, is_suspended=False,
                             limit_up=False, limit_down=False,
                             declining_count=count if symbol == "000001.SH" else None))
    return pd.DataFrame(rows)


@pytest.mark.parametrize("count,ret,expected", [(4000,-.01,True),(4001,-.02,True),
                                                (3999,-.02,False),(4500,-.009,False),
                                                (None,-.02,False),(float("nan"),-.02,False)])
def test_breadth_not_index_level(count, ret, expected):
    trigger = MarketTrigger(min_declining_count=4000, trigger_return_threshold=-.01)
    state = trigger.evaluate(3200, ret, date(2024,1,3), declining_count=count)
    assert state.triggered is expected


def test_backtest_and_recommendation_share_exact_signal_and_lots():
    data = sample()
    engine = BacktestEngine(10000, min_declining_count=4000, trigger_return_threshold=-.01,
                            commission_rate=0, stamp_duty_rate=0, minimum_commission=0,
                            slippage_bps=0, lot_size=100)
    result = engine.run(data, FixedAssetStrategy())
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert (trade.signal_date,trade.entry_date,trade.exit_date) == (date(2024,1,3),date(2024,1,4),date(2024,1,5))
    assert trade.quantity == 10000
    assert trade.pnl == pytest.approx(1000)
    assert sum(event["triggered"] for event in result.events) == 1
    strategy = FixedAssetStrategy()
    strategy.min_declining_count = 4000
    strategy.trigger_return_threshold = -.01
    rec = recommend(date(2024,1,3), data, strategy)
    assert rec.triggered and rec.selected.symbol == trade.symbol


def test_no_stale_market_signal_or_future_breadth():
    data = sample()
    data = data[~((data.date == "2024-01-04") & (data.symbol == "000001.SH"))]
    strategy = FixedAssetStrategy()
    strategy.min_declining_count = 4000
    strategy.trigger_return_threshold = -.01
    rec = recommend(date(2024,1,4),data,strategy)
    assert not rec.triggered
    assert any("missing" in warning for warning in rec.warnings)
    data.loc[data.date == "2024-01-03", "declining_count"] = None
    rec = recommend(date(2024,1,3),data,strategy)
    assert not rec.triggered
    assert any("breadth" in warning for warning in rec.warnings)


def test_breadth_csv_validation_and_join(tmp_path):
    from strategy.breadth import load_breadth, attach_breadth
    path = tmp_path / "breadth.csv"
    path.write_text("date,declining_count,total_count,source\n2024-01-03,4000,5100,test\n")
    frame = load_breadth(path)
    result = attach_breadth(sample().drop(columns="declining_count"), frame, "000001.SH")
    assert result[(result.symbol == "000001.SH") & (result.date == pd.Timestamp("2024-01-03"))].iloc[0].declining_count == 4000
    assert result.query("symbol == '588000.SH'").declining_count.isna().all()
    path.write_text("date,declining_count,total_count,source\n2024-01-03,4000,3000,test\n")
    with pytest.raises(ValueError,match="count"):
        load_breadth(path)


def test_quantity_respects_lots_and_commission_floor():
    engine = BacktestEngine(10000, lot_size=100, minimum_commission=5)
    quantity = engine._quantity(10000, 1.01)
    assert quantity % 100 == 0
    assert quantity * 1.01 + engine._commission(quantity * 1.01) <= 10000
    assert (quantity + 100) * 1.01 + engine._commission((quantity + 100) * 1.01) > 10000


def test_mvp_cli_compares_breadth_strategies(tmp_path, capsys):
    import json
    from pathlib import Path
    from strategy.cli import main
    config = Path(__file__).parents[1] / "configs/mvp.toml"
    assert main(["compare", "--config", str(config), "--output", str(tmp_path)]) == 0
    assert (tmp_path / "index.html").exists()
    report = json.loads((tmp_path / "fixed_asset/summary.json").read_text())
    assert report["metadata"]["sample"] is True
    assert report["metrics"]["trade_count"] > 0
    assert report["costs"]["stamp_duty_rate"] == 0


def test_cli_refuses_real_backtest_without_breadth(tmp_path):
    from strategy.cli import _load
    from pathlib import Path
    config = (Path(__file__).parents[1] / "configs/baseline.toml").read_text()
    path = Path(__file__).parents[1] / "data/sample/market.csv"
    config = config.replace("../data/sample/market.csv", str(path))
    config = config.replace("[market]", "[market]\nmin_declining_count = 4000")
    target = tmp_path / "missing.toml"
    target.write_text(config)
    with pytest.raises(ValueError, match="breadth"):
        _load(target)


def test_cli_rejects_unattributed_inline_breadth(tmp_path):
    from strategy.cli import _load
    sample().to_csv(tmp_path / "market.csv",index=False)
    (tmp_path / "test.toml").write_text('''[data]
source="unknown"
path="market.csv"
[strategy]
name="fixed_asset"
[backtest]
initial_cash=10000
[market]
min_declining_count=4000
trigger_return_threshold=-0.01
''')
    with pytest.raises(ValueError,match="breadth_path"):
        _load(tmp_path / "test.toml")


def test_cli_recommendation_discloses_sample(capsys):
    import json
    from pathlib import Path
    from strategy.cli import main
    config = Path(__file__).parents[1] / "configs/mvp.toml"
    assert main(["recommend", "--config", str(config), "--as-of", "2024-02-06"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["metadata"]["sample"] is True
    assert any("SYNTHETIC" in warning for warning in result["warnings"])
