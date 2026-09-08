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
      if (item.end < end) end = item.end;
    }
    return start <= end ? {start, end} : null;
  },
};
if (typeof module !== 'undefined') module.exports = InstrumentChoices;
