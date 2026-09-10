/* 可选标的与日期规则独立于 DOM，页面展示和提交前检查使用同一逻辑。 */
'use strict';
const InstrumentChoices = {
  available(dataset) {
    return (dataset?.instruments || []).filter(item => item.backtest_supported);
  },
  coverage(dataset, symbols) {
    if (!dataset || !symbols.length) return null;
    const available = this.available(dataset);
    let start = dataset.start, end = dataset.end;
    for (const symbol of symbols) {
      const item = available.find(candidate => candidate.symbol === symbol);
      if (!item) return null;
      if (item.start > start) start = item.start;
      // 行情可能早于已实现的费用规则，二者都必须覆盖回测区间。
      if (item.backtest_start > start) start = item.backtest_start;
      if (item.end < end) end = item.end;
    }
    return start <= end ? {start, end} : null;
  },
};
if (typeof module !== 'undefined') module.exports = InstrumentChoices;
