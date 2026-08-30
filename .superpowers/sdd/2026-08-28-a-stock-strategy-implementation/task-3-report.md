# Task 3 report: 日线回测撮合引擎

## Status

完成。新增 `src/strategy/backtest.py` 与 `tests/test_backtest.py`。

## Behavior

- 日线按日期稳定排序；策略只在收盘后收到 `date <= as_of` 的历史数据。
- 信号日之后的下一个交易日开盘撮合入场；默认持有一个交易日，在之后交易日开盘出场。
- 入场遇停牌、涨停或跌停不成交；出场遇停牌或跌停则保留仓位并在后续交易日重试。
- 现金、持仓市值、权益和回撤逐日记录。
- 买卖滑点、佣金、最低佣金和卖出印花税均可配置；成交价显式反映滑点。
- 末日无法安排下一交易日，或仓位没有可执行出场时，返回 `warnings`。

## Verification

`uv run --with pytest pytest tests/test_backtest.py -v` — 4 passed

`uv run --with pytest pytest -q` — 20 passed

`git diff --check` — passed

## Notes

`BacktestEngine` 在缺少指数行时将市场状态视为可触发，以便离线、单标的数据仍可运行；若存在 `index_symbol`，则按截至当日的指数收盘价计算触发状态。
