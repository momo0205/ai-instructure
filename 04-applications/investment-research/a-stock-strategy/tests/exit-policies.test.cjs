const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const file='../src/strategy/interfaces/web/static/exit-policies.js';
const x=fs.existsSync(require('node:path').resolve(__dirname,file))?require(file):{};
class Element {
 constructor(tag,text){this.tag=tag;this.children=[];this.textContent=text||'';this.value='';this.dataset={};}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=nodes;}
 setAttribute(){}
}
const el=(tag,text)=>new Element(tag,text),walk=n=>[n,...n.children.flatMap(walk)],text=n=>walk(n).map(e=>e.textContent).join(' ');
const catalog=[{id:'fixed_holding',name:'固定持有期',parameters:[],supports_effectiveness:true,supports_studies:true},{id:'close_below_sma',name:'收盘低于均线',description:'收盘检查，次日开盘卖出',supports_effectiveness:false,supports_studies:false,parameters:[{name:'window',label:'均线窗口',type:'integer',default:20,minimum:2,maximum:252},{name:'max_holding_days',label:'最长持有交易日',type:'integer',default:20,minimum:1,maximum:252}]}];
function editor(){assert.equal(typeof x.createEditor,'function');const nodes={select:el('select'),fields:el('div'),description:el('p'),holding:el('input'),effectiveness:el('input'),hint:el('p')};const view=x.createEditor({catalog,el,nodes,strategy:()=> 'fixed_asset'});return {nodes,view};}
test('catalogue renders bounded numeric controls and serializes only active exit parameters',()=>{
 const {view,nodes}=editor();view.restore({exit_policy:{id:'close_below_sma',parameters:{window:5,max_holding_days:12}}});
 const inputs=walk(nodes.fields).filter(n=>n.tag==='input');assert.equal(inputs.length,2);assert.equal(inputs[0].min,2);assert.equal(inputs[0].max,252);inputs[0].value='7';assert.deepEqual(view.read(),{id:'close_below_sma',parameters:{window:7,max_holding_days:12}});
 inputs[0].value='1';assert.throws(()=>view.read(),/均线窗口/);
});
test('copy restores both old and new requests, disables incompatible controls without duplicate holding days',()=>{
 const {view,nodes}=editor();nodes.effectiveness.checked=true;view.restore({exit_policy:{id:'close_below_sma',parameters:{window:6,max_holding_days:9}}});assert.equal(nodes.holding.disabled,true);assert.equal(nodes.effectiveness.disabled,true);assert.equal(nodes.effectiveness.checked,false);assert.match(nodes.hint.textContent,/退出.*暂不支持/);
 view.restore({holding_period_days:3});assert.deepEqual(view.read(),{id:'fixed_holding',parameters:{}});assert.equal(nodes.holding.disabled,false);assert.equal(nodes.effectiveness.disabled,false);
 assert.throws(()=>view.restore({exit_policy:{id:'unknown',parameters:{}}}),/不支持/);
});
test('rule labels omit inactive legacy holding days and retain every effective parameter',()=>{
 assert.equal(typeof x.label,'function');assert.match(x.label({holding_period_days:3}),/3/);
 const value=x.label({holding_period_days:999,exit_policy:{id:'close_below_sma',parameters:{window:5,max_holding_days:12}}});assert.match(value,/均线.*5.*12/);assert.doesNotMatch(value,/999/);
});
test('exit evidence shows unavailable warmup, planned next session and explicit legacy absence',()=>{
 assert.equal(typeof x.renderEvidence,'function');const root=el('div');x.renderEvidence(root,{},el);assert.match(text(root),/旧任务未记录退出证据/);
 x.renderEvidence(root,{exit_decision_events:[{date:'day1',symbol:'A',status:'indicator_unavailable',available:2,window:5,held_sessions:0},{date:'day2',symbol:'A',status:'triggered',close:9,sma:10,window:5,planned_exit_date:'day3',exit_signal_date:'day2',reason:'close_below_sma'}]},el);
 assert.match(text(root),/2.*5/);assert.match(text(root),/day3/);assert.match(text(root),/day2/);assert.match(text(root),/9/);assert.match(text(root),/10/);
});
test('indicator requests reject fixed holding study before constructing a batch',()=>{
 const {parseStudy}=require('../src/strategy/interfaces/web/static/studies.js');assert.throws(()=>parseStudy({job_id:'j',request:{start:'2024-01-01',end:'2024-12-31',exit_policy:{id:'close_below_sma'}}},'1,3','2024-07-01'),/固定.*退出/);
});
test('indicator rule explanation never promises fixed legacy exit timing',()=>{
 const h=require('../src/strategy/interfaces/web/static/explanations.js');const lines=h.ruleLines({strategy_id:'fixed_asset',holding_period_days:999,exit_policy:{id:'close_below_sma',parameters:{window:5,max_holding_days:12}}}).join(' ');assert.doesNotMatch(lines,/999/);assert.match(lines,/均线/);assert.match(lines,/次日|下一交易日/);
});
test('real form submit and copy preserve policy, and strategy switches cannot re-enable unsupported controls',()=>{
 const vm=require('node:vm'),nodes={};class Input extends Element{addEventListener(){} scrollIntoView(){} querySelectorAll(){return this.children.flatMap(c=>[...(c.dataset.parameter?[c]:[]),...c.querySelectorAll()]);}}
 const context=vm.createContext({document:{getElementById:id=>nodes[id]??=new Input('div'),createElement:tag=>new Input(tag)},Option:class extends Input{constructor(text,value){super('option',text);this.value=value;}},InstrumentChoices:require('../src/strategy/interfaces/web/static/instrument-options.js'),setInterval(){}});
 for(const name of ['exit-policies','explanations','app'])vm.runInContext(fs.readFileSync(`src/strategy/interfaces/web/static/${name}.js`,'utf8').replace('init().catch(e=>notice(e.message));',''),context);
 vm.runInContext(`state.datasets=[{id:'d',start:'2024-01-01',end:'2024-12-31',instruments:[{symbol:'A',backtest_supported:true,start:'2024-01-01',end:'2024-12-31'}]}];state.strategies=[{id:'fixed_asset',parameters:[{name:'symbol',type:'string',role:'instrument',default:'A'}]}];$('dataset').value='d';$('strategy').value='fixed_asset';initExitEditor(${JSON.stringify(catalog)});copyRequest({strategy_id:'fixed_asset',dataset_id:'d',parameters:{symbol:'A'},holding_period_days:999,exit_policy:{id:'close_below_sma',parameters:{window:4,max_holding_days:8}}});`,context);
 const control=nodes['strategy-parameters'].querySelectorAll()[0];control.value='A';
 const request=JSON.parse(vm.runInContext('JSON.stringify(requestFromForm())',context));assert.deepEqual(request.exit_policy,{id:'close_below_sma',parameters:{window:4,max_holding_days:8}});assert.equal(request.effectiveness,false);assert.equal(request.holding_period_days,undefined);
 vm.runInContext('strategyFields()',context);assert.equal(nodes.effectiveness.disabled,true);
 assert.doesNotMatch(text(nodes['strategy-rule']),/999/);
});
test('evidence exposes actual frozen warmup coverage and policy version even with no holdings',()=>{
 const root=el('div');x.renderEvidence(root,{metadata:{exit_policy:{id:'close_below_sma',version:'sma-exit-v1',parameters:{window:5,max_holding_days:8}},exit_warmup:{A:{required_prior_sessions:4,available_prior_sessions:2,ready_at_start:false}}},exit_decision_events:[]},el);
 assert.match(text(root),/sma-exit-v1/);assert.match(text(root),/A.*2.*4/);assert.match(text(root),/不足/);
});
test('trade exit signal is read from matching filled execution evidence',()=>{
 assert.equal(typeof x.tradeExitSignal,'function');
 const trade={symbol:'A',entry_date:'2026-01-02',exit_date:'2026-01-05'};
 const events=[{side:'sell',status:'filled',symbol:'B',entry_date:trade.entry_date,date:trade.exit_date,exit_signal_date:'wrong'}, {side:'sell',status:'filled',symbol:'A',entry_date:trade.entry_date,date:trade.exit_date,exit_signal_date:'2026-01-03'}];
 assert.equal(x.tradeExitSignal(trade,events),'2026-01-03');assert.equal(x.tradeExitSignal(trade,[]),null);
});
test('native select input before change does not read stale parameter controls',()=>{
 const {view,nodes}=editor();nodes.select.value='close_below_sma';
 assert.deepEqual(view.read(false),{id:'close_below_sma',parameters:{window:20,max_holding_days:20}});
});
test('execution timeline shows both exit intent and a deferred execution cause',()=>{
 const {executionRow}=require('../src/strategy/interfaces/web/static/explanations.js');
 assert.match(executionRow({side:'sell',status:'filled',reason:'',exit_reason:'close_below_sma'}).join(' '),/收盘低于均线/);
 const delayed=executionRow({side:'sell',status:'deferred',reason:'limit_down',exit_reason:'close_below_sma'}).join(' ');
 assert.match(delayed,/已知跌停/);assert.match(delayed,/收盘低于均线/);
});
