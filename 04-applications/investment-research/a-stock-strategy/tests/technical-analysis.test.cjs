const {test} = require('node:test');
const assert = require('node:assert/strict');
const analysis = require('../src/strategy/interfaces/web/static/technical-analysis.js');

test('catalog groups source and derived definitions for one library view', () => {
  const entries = [
    {id:'ohlc',category:'price',kind:'source'},
    {id:'sma',category:'trend',kind:'derived',parameters:[{name:'window',default:20}]},
    {id:'ema',category:'trend',kind:'derived',parameters:[{name:'window',default:20}]},
  ];
  assert.deepEqual(analysis.groupCatalog(entries).map(group => [group.id,group.entries.length]),
    [['price',1],['trend',2]]);
  assert.deepEqual(analysis.createInstance(entries,'sma',[]),
    {instance_id:'sma_1',id:'sma',parameters:{window:20}});
  assert.equal(analysis.createInstance(entries,'sma',[{instance_id:'sma_1'}]).instance_id,'sma_2');
});

test('request keeps one selected version and independent indicator instances', () => {
  const items = [{instance_id:'sma_1',id:'sma',parameters:{window:5}},
    {instance_id:'sma_2',id:'sma',parameters:{window:20}}];
  assert.deepEqual(analysis.buildRequest({id:'asset_a',symbol:'600519.SH'},'2026-01-01','2026-01-31',items),{
    source_id:'asset_a',symbol:'600519.SH',start:'2026-01-01',end:'2026-01-31',indicators:items,
  });
});

test('late responses cannot replace a newer choice', () => {
  const gate = analysis.createRequestGate();
  const first = gate.next();
  const second = gate.next();
  assert.equal(gate.current(first),false);
  assert.equal(gate.current(second),true);
});

test('table pages exact values and export retains source and every row', () => {
  const rows = Array.from({length:27},(_,i)=>({date:`day-${i}`,indicators:{x:{values:{value:i}}}}));
  const result = {source:{id:'asset_a',market_sha256:'hash'},rows};
  assert.equal(analysis.pageRows(rows,1,25).length,25);
  assert.deepEqual(analysis.pageRows(rows,2,25).map(row=>row.date),['day-25','day-26']);
  assert.deepEqual(JSON.parse(analysis.serializeExport(result)),result);
});

test('chart model shares visible date range and exact inspected row', () => {
  const rows = Array.from({length:300},(_,i)=>({date:`day-${i}`,close:i+1,volume:i}));
  const view = analysis.visibleRows(rows,60,10);
  assert.equal(view.length,60);
  assert.equal(view[0].date,'day-230');
  assert.equal(analysis.rowAtRatio(view,.5).date,'day-260');
});

test('chart lines stay separated across an unsampled missing date', () => {
  const rows = Array.from({length:300},(_,i)=>({indicators:{a:{values:{value:i===151?null:i}}}}));
  const segments = analysis.chartSegments(rows,'a','value',20);
  assert.equal(segments.length,2);
  assert.equal(segments[0].at(-1)[0],150);
  assert.equal(segments[1][0][0],152);
});

test('chart bounds ignore unavailable values and handle full allowed history', () => {
  const values = Array.from({length:5000},(_,i)=>i);
  assert.deepEqual(analysis.chartBounds([null,NaN,...values]),[0,4999]);
  assert.deepEqual(analysis.chartBounds([null,NaN]),null);
});

test('legend identifies every independently configured line', () => {
  const instances=[
    {instance_id:'sma_1',name:'简单均线 SMA',parameters:{window:5},outputs:[{name:'value'}],panel:'price'},
    {instance_id:'sma_2',name:'简单均线 SMA',parameters:{window:20},outputs:[{name:'value'}],panel:'price'},
  ];
  assert.deepEqual(analysis.legendEntries(instances).map(item=>item.label),
    ['简单均线 SMA(5) · value','简单均线 SMA(20) · value']);
});

test('moving the chart window also moves inspection to a visible date', () => {
  const rows=[{date:'day-1'},{date:'day-2'},{date:'day-3'}];
  assert.equal(analysis.visibleSelection(rows,'day-2'),'day-2');
  assert.equal(analysis.visibleSelection(rows,'day-9'),'day-3');
});

test('quote labels distinguish missing quote from unknown trading status', () => {
  assert.match(analysis.quoteLabel({status:'observed_quote',trading_status:'unknown'}),/交易状态未知/);
  assert.match(analysis.quoteLabel({status:'missing_quote'}),/缺少证券行情/);
  assert.match(analysis.quoteLabel({status:'suspended_quote',trading_status:'suspended'}),/停牌报价/);
});
