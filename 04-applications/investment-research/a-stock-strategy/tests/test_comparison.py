import json
from dataclasses import replace

import pandas as pd
import pytest

from strategy.config import BacktestConfig, BacktestSettings, CostConfig, DataConfig, MarketConfig, StrategyConfig


def fixture():
    rows = []
    for i, day in enumerate(pd.bdate_range('2026-07-01', periods=30)):
        for symbol in ['000001.SH', '588000.SH', '510300.SH']:
            price = (4200 if i < 22 else 4100) if symbol == '000001.SH' else (1 + i * (.01 if symbol == '588000.SH' else .02))
            rows.append(dict(date=day, symbol=symbol, open=price, high=price * 1.01,
                             low=price * .99, close=price, volume=10000, amount=10000,
                             declining_count=4500, is_suspended=False, limit_up=False, limit_down=False))
    config = BacktestConfig(DataConfig('fixture', 'sample.csv'),
        StrategyConfig('fixed_asset', {'symbol': '588000.SH', 'candidate_symbols': ['588000.SH', '510300.SH']}),
        BacktestSettings(100000), MarketConfig(trigger_return_threshold=-.01), CostConfig(),
        {'sample': True, 'source': '<script>alert(1)</script>', 'breadth_source': 'synthetic', 'warnings': ['样例广度']})
    return config, pd.DataFrame(rows)


def test_comparison_uses_fixed_equity_as_benchmark_and_writes_reviewable_report(tmp_path):
    from strategy.comparison import compare
    config, data = fixture()
    original = data.copy(deep=True)
    payload = compare(config, data, tmp_path)
    fixed, dynamic = payload['strategies']['fixed_asset'], payload['strategies']['cross_sectional_rank']
    assert fixed['metrics']['benchmark_return'] is None
    assert dynamic['metrics']['benchmark_return'] == pytest.approx(fixed['metrics']['cumulative_return'])
    assert fixed['metrics']['trade_count'] > 0
    assert dynamic['metrics']['trade_count'] > 0
    assert dynamic['metrics']['cumulative_return'] != fixed['metrics']['cumulative_return']
    assert pd.read_csv(tmp_path / 'comparison.csv').shape[0] == 2
    assert json.loads((tmp_path / 'comparison.json').read_text())['metadata']['costs']['commission_rate'] == config.costs.commission_rate
    for key in ['fixed_asset', 'cross_sectional_rank']:
        for name in ['trades.csv', 'equity.csv', 'summary.json', 'report.png']:
            assert (tmp_path / key / name).is_file()
    html = (tmp_path / 'index.html').read_text()
    for word in ['D+1', 'D+2', '不是同日尾盘', '样例收益不可作策略结论', 'ETF价格特征评分', '样例广度', '胜率', '最大回撤', '交易次数']:
        assert word in html
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html
    assert 'data:image/png;base64,' in html
    assert 'fixed_asset/trades.csv' in html
    pd.testing.assert_frame_equal(data, original)


def test_single_candidate_is_explicitly_not_dynamic_comparison(tmp_path):
    from strategy.comparison import compare
    config, data = fixture()
    config = replace(config, strategy=StrategyConfig('fixed_asset', {'symbol': '588000.SH'}))
    payload = compare(config, data, tmp_path)
    assert any('无动态比较意义' in warning for warning in payload['warnings'])


def test_comparison_exports_daily_trigger_audit_and_effective_strategy(tmp_path):
    from strategy.comparison import compare
    config, data = fixture()
    config = replace(config, market=replace(config.market, min_declining_count=4000))
    compare(config, data, tmp_path)
    events = pd.read_csv(tmp_path / 'cross_sectional_rank' / 'events.csv')
    assert events['triggered'].sum() == 1
    assert events.loc[events['triggered'], 'declining_count'].iloc[0] == 4500
    assert events.loc[events['triggered'], 'index_return_1d'].iloc[0] < -.01
    summary = json.loads((tmp_path / 'cross_sectional_rank' / 'summary.json').read_text())
    assert summary['metadata']['strategy']['name'] == 'cross_sectional_rank'
    assert 'symbol' not in summary['metadata']['strategy']['parameters']
    assert 'cross_sectional_rank/events.csv' in (tmp_path / 'index.html').read_text()
def test_compare_rejects_absent_candidate_data(tmp_path):
    from pathlib import Path
    from strategy.cli import _load
    from strategy.comparison import compare
    import pytest
    config, data = _load(Path(__file__).parents[1] / "configs/mvp.toml")
    data = data[data.symbol != "588000.SH"]
    with pytest.raises(ValueError, match="588000.SH"):
        compare(config, data, tmp_path)


def test_compare_warns_stale_etf_is_not_valid_zero_return_baseline(tmp_path):
    from pathlib import Path
    from strategy.cli import _load
    from strategy.comparison import compare
    config, data = _load(Path(__file__).parents[1] / "configs/mvp.toml")
    data = data[(data.symbol != "588000.SH") | (data.date == data.date.min())]
    result = compare(config, data, tmp_path)
    assert any("588000.SH" in w and "missing" in w for w in result["warnings"])
    assert result["metadata"]["data_coverage"]["588000.SH"]["missing_sessions"] > 0
    assert result["strategies"]["cross_sectional_rank"]["metrics"]["excess_return"] is None
