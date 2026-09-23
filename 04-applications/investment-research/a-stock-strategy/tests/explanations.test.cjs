const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path='../src/strategy/interfaces/web/static/explanations.js';
const x=fs.existsSync(require('node:path').resolve(__dirname,path))?require(path):{};
test('momentum rules expose exact units, timing and engine boundary',()=>{
 assert.equal(typeof x.ruleLines,'function');
 const rules=x.ruleLines({strategy_id:'qlib_momentum',parameters:{lookback:2,minimum_momentum:-1,candidate_symbols:['A','B']},holding_period_days:3,min_declining_count:4000,trigger_return_threshold:-.01}).join('\n');
 for(const pattern of [/2 个交易日/,/− 1/,/−?100%|-100%/,/3 个交易日/,/Qlib/,/不换仓/,/A、B/,/-1%/]) assert.match(rules,pattern);
});
test('untriggered and holding days never imply candidate evaluation',()=>{
 assert.equal(typeof x.decisionSummary,'function');
 assert.match(x.decisionSummary({status:'market_not_triggered'}),/未计算/);
 assert.match(x.decisionSummary({status:'holding',position_symbol:'A'}),/A.*未计算/);
 assert.match(x.decisionSummary({status:'no_next_session',selected_symbol:'A'}),/无下一交易日/);
});
test('missing factor and tie reasons remain explicit',()=>{
 assert.equal(typeof x.reasonText,'function');
 assert.match(x.reasonText('missing_factor'),/因子/);
 assert.match(x.reasonText('tie_break'),/同分.*代码/);
 assert.match(x.reasonText('unknown'),/unknown/);
});
test('timeline distinguishes plan, actual cancellation and unknown exit calendar',()=>{
 assert.equal(typeof x.executionRow,'function');
 const row=x.executionRow({date:'2024-01-03',symbol:'A',side:'buy',status:'cancelled',signal_date:'2024-01-02',entry_date:null,planned_exit_date:null,reason:'insufficient cash'}).join(' ');
 assert.match(row,/2024-01-02/);assert.match(row,/取消/);assert.match(row,/未知|未确定/);assert.match(row,/资金不足/);
});
// Minimal DOM exercises our renderer without a browser dependency.
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.textContent='';this.value='';}
 append(...nodes){this.children.push(...nodes);if(this.tag==='select'&&this.children.length)this.value=this.children[0].value;}
 replaceChildren(...nodes){this.children=nodes;}
 setAttribute(){}
 set innerHTML(value){throw Error('unsafe HTML');}
}
const walk=n=>[n,...n.children.flatMap(walk)];
const text=n=>walk(n).map(e=>e.textContent).join(' ');
global.document={createElement:tag=>new Element(tag)};
test('old results request rerun rather than fabricating empty decisions',()=>{
 const root=new Element('section');x.renderResult(root,{},{strategy_id:'fixed_asset',parameters:{symbol:'A'}});
 assert.match(text(root),/复制参数重跑/);assert.doesNotMatch(text(root),/没有执行事件/);
});
test('candidate rendering is text-safe and changes one date at a time',()=>{
 const root=new Element('section');x.renderResult(root,{decision_events:[{date:'2024-01-02',status:'selected',selected_symbol:'<img>',market_triggered:true,candidates:[{symbol:'<img>',status:'selected',reason:'selected',score:.08,reference_close:100,current_close:108}]},{date:'2024-01-03',status:'holding',position_symbol:'<img>',candidates:[]}]},{strategy_id:'price_momentum'});
 assert.match(text(root),/<img>/);assert.match(text(root),/8%/);
 const select=walk(root).find(n=>n.tag==='select');select.value='1';select.onchange();
 assert.match(text(root),/未计算候选分数/);assert.doesNotMatch(text(root),/8%/);
});
test('timeline bounds rendered event count and pages all events',()=>{
 const root=new Element('section');x.renderResult(root,{decision_events:[],execution_events:Array.from({length:21},(_,i)=>({date:`event-${i}`,symbol:'A',side:'buy',status:'filled'}))},{strategy_id:'fixed_asset'});
 assert.match(text(root),/event-19/);assert.doesNotMatch(text(root),/event-20/);
 walk(root).find(n=>n.textContent==='下一页').onclick();assert.match(text(root),/event-20/);assert.doesNotMatch(text(root),/event-19/);
});
test('timeline includes planned entry separately from actual execution',()=>{
 assert.ok(x.executionRow({signal_date:'signal',planned_entry_date:'planned',date:'attempt',entry_date:'actual'}).includes('planned'));
});
test('rules explain candidate filters, index identity and unknown status assumption',()=>{
 const lines=x.ruleLines({strategy_id:'price_momentum'}).join(' ');
 assert.match(lines,/000001.SH/);assert.match(lines,/停牌.*涨跌停/);assert.match(lines,/False.*已验证/);
});
test('execution block codes are understandable without backend vocabulary',()=>{
 for(const [code,label] of [['insufficient_cash','资金不足'],['missing_row','缺少当日行情'],['invalid_open','开盘价无效'],['suspended','已知停牌']])assert.equal(x.reasonText(code),label);
});
test('unavailable market data displays warning and unknown return, not ordinary non-trigger',()=>{
 const root=new Element('section');x.renderResult(root,{decision_events:[{date:'2024-01-02',status:'market_data_unavailable',index_return_1d:null,market_triggered:false,market_warning:'missing previous index close',candidate_details_supported:false}]},{strategy_id:'price_momentum'});
 assert.match(text(root),/市场数据不可用/);assert.match(text(root),/missing previous index close/);assert.match(text(root),/指数日收益 —/);assert.match(text(root),/市场触发：无法判断/);assert.doesNotMatch(text(root),/不支持逐候选/);
});
test('explicit unsupported evaluation does not show misleading candidate scores',()=>{
 const root=new Element('section');x.renderResult(root,{decision_events:[{date:'2024-01-02',status:'selected',candidate_details_supported:false,candidates:[{symbol:'A',score:.12345}]}]},{strategy_id:'price_momentum'});
 assert.match(text(root),/不支持逐候选/);assert.doesNotMatch(text(root),/12.345%/);
});
test('holding skip is not described as unsupported evaluation',()=>{
 const root=new Element('section');x.renderResult(root,{decision_events:[{date:'2024-01-02',status:'holding',candidate_details_supported:false,candidates:[]}]},{strategy_id:'price_momentum'});
 assert.match(text(root),/未计算/);assert.doesNotMatch(text(root),/不支持逐候选/);
});
