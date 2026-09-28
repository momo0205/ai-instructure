const {test} = require('node:test');
const assert = require('node:assert/strict');
const choices = require('../src/strategy/interfaces/web/static/instrument-options.js');
const dataset = {start:'2024-01-02',end:'2025-12-31', instruments:[
  {symbol:'588000.SH',name:'科创50 ETF',backtest_supported:true,start:'2024-01-02',end:'2025-12-31'},
  {symbol:'510300.SH',name:'沪深300 ETF',backtest_supported:true,start:'2024-06-01',end:'2025-12-01'},
  {symbol:'002015.SZ',name:'协鑫能科',backtest_supported:false,start:'2024-01-02',end:'2025-12-31'},
]};
test('only supported prepared instruments are selectable',()=>{
  assert.deepEqual(choices.available(dataset).map(x=>x.symbol),['588000.SH','510300.SH']);
});
test('selected instruments use intersected coverage',()=>{
  assert.deepEqual(choices.coverage(dataset,['588000.SH','510300.SH']),{start:'2024-06-01',end:'2025-12-01'});
});
test('missing or unsupported symbols never silently become valid',()=>{
  assert.equal(choices.coverage(dataset,['002015.SZ']),null);
  assert.equal(choices.coverage(dataset,['MISSING']),null);
  assert.equal(choices.coverage(dataset,[]),null);
});
test('non-overlapping coverage blocks submission',()=>{
  const partial={...dataset,instruments:[{symbol:'X',backtest_supported:true,start:'2026-01-01',end:'2026-02-01'}]};
  assert.equal(choices.coverage(partial,['X']),null);
});

test('stock coverage respects the implemented fee-rule start',()=>{
  const d={start:'2020-01-01',end:'2025-12-31',instruments:[{symbol:'002015.SZ',backtest_supported:true,start:'2020-01-01',end:'2025-12-31',backtest_start:'2022-07-01'}]};
  assert.deepEqual(choices.coverage(d,['002015.SZ']),{start:'2022-07-01',end:'2025-12-31'});
});
