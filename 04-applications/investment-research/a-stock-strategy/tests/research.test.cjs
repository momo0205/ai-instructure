const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path='../src/strategy/interfaces/web/static/research.js';
test('comparison flags incompatible inputs and highlights changed parameters',()=>{
 const h=require(path);const a={request:{start:'2024-01-01',end:'2024-12-31',initial_cash:100000,commission_rate:0.001,parameters:{assets:['X'],history:3}},data_version:'v1'};
 const b={...a,request:{...a.request,start:'2024-02-01',initial_cash:200000,commission_rate:0.002,parameters:{assets:['X'],history:7}},data_version:'v2'};
 assert.deepEqual(h.changedParameters([a,b]),['history']);
 const warnings=h.comparisonWarnings([a,b]).join(' ');for(const term of ['区间','数据版本','初始资金','成本'])assert.match(warnings,new RegExp(term));
 assert.deepEqual(h.comparisonWarnings([a,a]),[]);
});
test('missing metrics stay empty and no-trade win rate is unavailable',()=>{
 const h=require(path);assert.equal(h.metric({},'cumulative_return'),'—');assert.equal(h.metric({trade_count:0,win_rate:0},'win_rate'),'—');assert.equal(h.metric({cumulative_return:0},'cumulative_return'),'0.00%');assert.equal(h.metric({trade_count:0},'trade_count'),'0');
});
test('filter finds notes strategy and instruments; comparison caps selection at four',()=>{
 const h=require(path);const item={name:'实验甲',notes:'低成本',request:{strategy_id:'fixed_asset',parameters:{assets:['588000.SH']}}};
 assert.equal(h.matches(item,'低成本'),true);assert.equal(h.matches(item,'588000'),true);assert.equal(h.matches(item,'不存在'),false);
 const selected=new Set(['1','2','3','4']);assert.equal(h.toggleSelection(selected,'5',true),false);assert.equal(selected.size,4);assert.equal(h.toggleSelection(selected,'2',false),true);
});
class Element {
 constructor(tag,text){this.tagName=tag;this.textContent=text;this.children=[];this.value='';}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=nodes;}
 setAttribute(){}
 focus(){}
}
const all=node=>[node,...node.children.flatMap(all)];
test('page loads only on demand, filters, edits labels and routes detail and rerun',async()=>{
 const {createResearch}=require(path),nodes=Object.fromEntries(['status','filter','strategy','list','comparison','editor','refresh','advanced'].map(key=>[key,new Element('div')]));
 const calls=[],actions=[];let item={job_id:'abc',name:'名称',notes:'观察',request:{strategy_id:'fixed',parameters:{asset:'X'}},metrics:{cumulative_return:0},controls:{}};
 const view=createResearch({nodes,el:(tag,text)=>new Element(tag,text),strategyName:()=> '固定策略',strategies:()=>[{id:'fixed',parameters:[{name:'asset',role:'instrument'}]}],api:async(url,body)=>{calls.push([url,body]);if(url==='/api/experiments')return {enabled:true,ui_url:'http://127.0.0.1:5000'};if(body){item={...item,...body};return body;}return {enabled:true,items:[item],limit:200};},showJob:async id=>actions.push(id),copyRequest:request=>actions.push(request),activateTab:id=>actions.push(id)});
 assert.equal(calls.length,0);await view.open();await view.open();assert.equal(calls.length,2);
 assert.match(all(nodes.list).map(n=>n.textContent||'').join(' '),/固定策略 \/ X/);
 assert.equal(all(nodes.advanced).find(n=>n.tagName==='details').open,undefined);
 const buttons=all(nodes.list).filter(n=>n.tagName==='button');await buttons[0].onclick();await buttons[1].onclick();assert.deepEqual(actions,['abc','research',item.request]);
 await buttons[2].onclick();const editor=nodes.editor.children[0],inputs=all(editor);inputs.find(n=>n.tagName==='input').value='新名称';inputs.find(n=>n.tagName==='textarea').value='新备注';await editor.onsubmit({preventDefault(){}});
 assert.deepEqual(calls.find(([url])=>url.endsWith('/experiment-label')),['/api/jobs/abc/experiment-label',{name:'新名称',notes:'新备注'}]);
 assert.equal(calls.length,5);assert.match(all(nodes.list).map(n=>n.textContent||'').join(' '),/新名称/);
 nodes.filter.value='不存在';nodes.filter.oninput();assert.match(all(nodes.list).map(n=>n.textContent||'').join(' '),/没有符合/);
});
test('unknown data versions do not imply comparability and source versions are compared',()=>{
 const h=require(path);assert.match(h.comparisonWarnings([{data_version:null},{data_version:'unknown'}]).join(' '),/版本缺失/);
 assert.match(h.comparisonWarnings([{data_version:'v1',source_snapshot:'a'},{data_version:'v1',source_snapshot:'b'}]).join(' '),/源码/);
});
test('unnamed experiments have Chinese titles and comparison renders changed fields and readable rates',async()=>{
 const {createResearch}=require(path),nodes=Object.fromEntries(['status','filter','strategy','list','comparison','editor','refresh','advanced'].map(key=>[key,new Element('div')]));
 const items=Array.from({length:5},(_,n)=>({job_id:String(n),name:'',data_version:'v1',request:{strategy_id:'fixed',holding_period_days:3,parameters:{asset:'X',window:n},commission_rate:0.001,trigger_return_threshold:-0.01},metrics:{trade_count:0,win_rate:0},controls:{random_percentile:75}}));
 const view=createResearch({nodes,el:(tag,text)=>new Element(tag,text),strategyName:()=> '固定策略',strategies:()=>[{id:'fixed',parameters:[{name:'asset',role:'instrument'}]}],api:async url=>url==='/api/experiments'?{enabled:false}:{enabled:true,items},showJob(){},copyRequest(){},activateTab(){}});
 await view.open();assert.match(all(nodes.list).map(n=>n.textContent||'').join(' '),/固定策略 · X · 持有 3 天/);
 const checks=all(nodes.list).filter(n=>n.tagName==='input');for(const check of checks){check.checked=true;check.onchange();}
 assert.equal(checks[4].checked,false);assert.match(nodes.status.textContent,/最多同时比较 4/);
 const text=all(nodes.comparison).map(n=>n.textContent||'').join(' ');for(const pattern of [/变化 · window/,/0.10%/,/-1.00%/,/第 75.00 百分位/,/胜率.*—/])assert.match(text,pattern);
});
test('loading failures can be retried and empty results guide history synchronization',async()=>{
 const {createResearch}=require(path),nodes=Object.fromEntries(['status','filter','strategy','list','comparison','editor','refresh','advanced'].map(key=>[key,new Element('div')]));let fail=true;
 const view=createResearch({nodes,el:(tag,text)=>new Element(tag,text),strategyName:id=>id,strategies:()=>[],api:async()=>{if(fail)throw new Error('服务不可用');return {enabled:false,items:[]};}});
 await view.open();assert.match(nodes.status.textContent,/加载失败/);assert.equal(nodes.refresh.disabled,false);
 fail=false;await view.open();assert.match(nodes.status.textContent,/尚未启用/);assert.match(all(nodes.list).map(n=>n.textContent||'').join(' '),/任务历史/);assert.equal(nodes.advanced.children.length,0);
});
test('list and comparison identify synthetic sample data explicitly',async()=>{
 const {createResearch}=require(path),nodes=Object.fromEntries(['status','filter','strategy','list','comparison','editor','refresh','advanced'].map(key=>[key,new Element('div')]));
 const items=['mvp_sample','real_daily'].map((dataset_id,n)=>({job_id:String(n),name:'实验',request:{dataset_id},metrics:{},controls:{}}));
 const view=createResearch({nodes,el:(tag,text)=>new Element(tag,text),strategyName:id=>id,strategies:()=>[],api:async url=>url==='/api/experiments'?{enabled:false}:{enabled:true,items}});
 await view.open();let text=all(nodes.list).map(n=>n.textContent||'').join(' ');assert.match(text,/合成样例/);assert.match(text,/real_daily/);
 for(const check of all(nodes.list).filter(n=>n.tagName==='input')){check.checked=true;check.onchange();}
 text=all(nodes.comparison).map(n=>n.textContent||'').join(' ');assert.match(text,/数据集.*合成样例.*real_daily/);
});
test('default displayed Chinese name is searchable',async()=>{
 const {createResearch}=require(path),nodes=Object.fromEntries(['status','filter','strategy','list','comparison','editor','refresh','advanced'].map(key=>[key,new Element('div')]));
 const view=createResearch({nodes,el:(tag,text)=>new Element(tag,text),strategyName:()=> '中文策略',strategies:()=>[],api:async url=>url==='/api/experiments'?{enabled:false}:{enabled:true,items:[{job_id:'a',name:'',request:{holding_period_days:3},metrics:{}}]}});
 await view.open();nodes.filter.value='持有 3 天';nodes.filter.oninput();assert.ok(all(nodes.list).some(n=>n.tagName==='strong'));
});
test('old save cannot close a newer editor and saves queue a fresh read after ongoing refresh',async()=>{
 const {createResearch}=require(path),nodes=Object.fromEntries(['status','filter','strategy','list','comparison','editor','refresh','advanced'].map(key=>[key,new Element('div')]));
 let items=[{job_id:'a',name:'甲',request:{},metrics:{}},{job_id:'b',name:'乙',request:{},metrics:{}}],finishSave,finishRead,blockRead=false,reads=0;
 const view=createResearch({nodes,el:(tag,text)=>new Element(tag,text),strategyName:()=> '策略',strategies:()=>[],api:async(url,body)=>{
  if(url==='/api/experiments')return {enabled:false};
  if(body){await new Promise(resolve=>finishSave=resolve);items=items.map(i=>i.job_id==='a'?{...i,...body}:i);return body;}
  reads++;const snapshot=items.map(i=>({...i}));if(blockRead)await new Promise(resolve=>finishRead=resolve);return {enabled:true,items:snapshot};
 }});
 await view.open();const edits=all(nodes.list).filter(n=>n.tagName==='button'&&n.textContent==='编辑');await edits[0].onclick();
 const first=nodes.editor.children[0],input=all(first).find(n=>n.tagName==='input');input.value='甲新';
 blockRead=true;const refreshing=view.load();const saving=first.onsubmit({preventDefault(){}});
 assert.equal(input.disabled,true);await edits[1].onclick();const newer=nodes.editor.children[0];
 finishSave();await Promise.resolve();blockRead=false;finishRead();await refreshing;await saving;
 assert.equal(nodes.editor.children[0],newer);assert.equal(reads,3);assert.match(all(nodes.list).map(n=>n.textContent||'').join(' '),/甲新/);
});
test('batch validation action passes the selected experiment as base',async()=>{
 const {createResearch}=require(path),nodes=Object.fromEntries(['status','filter','strategy','list','comparison','editor','refresh','advanced'].map(key=>[key,new Element('div')]));const item={job_id:'base-study',request:{strategy_id:'fixed',start:'2024-01-01',end:'2024-12-31'}};let received;
 const view=createResearch({nodes,el:(tag,text)=>new Element(tag,text),strategyName:id=>id,strategies:()=>[],beginStudy:base=>{received=base;},api:async url=>url==='/api/experiments'?{enabled:false}:{enabled:true,items:[item]}});
 await view.open();await all(nodes.list).find(node=>node.tagName==='button'&&node.textContent==='批量验证').onclick();assert.equal(received,item);
});
test('browser bootstrap works before studies script loads',()=>{
 const vm=require('node:vm');const nodes=new Map();
 const context={document:{getElementById:id=>{if(!nodes.has(id))nodes.set(id,new Element('div'));const n=nodes.get(id);n.hidden=true;return n;}},MutationObserver:class{observe(){}},api:async()=>({}),el:(tag,text)=>new Element(tag,text),strategyName:id=>id,state:{strategies:[]},showJob(){},copyRequest(){},activateTab(){}};
 vm.runInNewContext(fs.readFileSync(require.resolve(path),'utf8'),context);
 assert.ok(context.ResearchExperiments);
});
