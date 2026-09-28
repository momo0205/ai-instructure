const {test}=require('node:test');
const assert=require('node:assert/strict');
const path='../src/strategy/interfaces/web/static/studies.js';
class Element{
 constructor(tag,text){this.tagName=tag;this.textContent=text;this.children=[];this.value='';}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=nodes;}
 setAttribute(){}
 focus(){}
 scrollIntoView(){}
}
const all=node=>[node,...node.children.flatMap(all)];
const base={job_id:'base',name:'原实验',request:{start:'2024-01-01',end:'2024-12-31'}};
function nodes(){return Object.fromEntries(['status','form','list','detail','refresh'].map(key=>[key,new Element('div')]));}
test('batch candidates and validation split reject ambiguous or out-of-range input',()=>{
 const h=require(path);assert.deepEqual(h.parseStudy(base,'1,3,5','2024-07-01'),{base_job_id:'base',holding_periods:[1,3,5],validation_start:'2024-07-01'});
 for(const value of ['1','1,1','0,2','1,253','1,1.5','1,,3','1,2,3,4,5,6,7,8,9','1e1,3'])assert.throws(()=>h.parseStudy(base,value,'2024-07-01'));
 for(const value of ['2024-01-01','2025-01-01','2024-02-30',''])assert.throws(()=>h.parseStudy(base,'1,3',value));
});
test('batch form submits protocol then renders training separately from validation and cancels',async()=>{
 const h=require(path),n=nodes(),calls=[];let study={id:'s1',status:'selecting',selection_start:'2024-01-01',selection_end:'2024-06-30',validation_start:'2024-07-01',validation_end:'2024-12-31',training:[{holding_period_days:1,job_id:'j1',status:'succeeded',metrics:{cumulative_return:0.1,trade_count:1}}],validation:null};
 const view=h.createStudies({nodes:n,el:(tag,text)=>new Element(tag,text),visible:()=>true,showJob:async id=>calls.push(['show',id]),activateTab:id=>calls.push(['tab',id]),api:async(url,body)=>{calls.push([url,body]);if(url.endsWith('/cancel'))study={...study,status:'cancelled'};return url==='/api/studies'&&!body?{items:[study]}:study;}});
 view.openForm(base);const form=n.form.children[0];const inputs=all(form).filter(x=>x.tagName==='input');inputs[0].value='1,3,5';inputs[1].value='2024-07-01';await form.onsubmit({preventDefault(){}});
 assert.deepEqual(calls[0],['/api/studies',{base_job_id:'base',holding_periods:[1,3,5],validation_start:'2024-07-01'}]);
 assert.match(all(n.detail).map(x=>x.textContent||'').join(' '),/前段.*后段/s);
 await all(n.detail).find(x=>x.tagName==='button'&&x.textContent==='查看回测详情').onclick();assert.ok(calls.some(x=>x[0]==='show'&&x[1]==='j1'));
 await all(n.detail).find(x=>x.tagName==='button'&&x.textContent==='取消批量验证').onclick();assert.ok(calls.some(x=>x[0]==='/api/studies/s1/cancel'));assert.match(all(n.detail).map(x=>x.textContent||'').join(' '),/已取消/);
});
test('study polling only reads study APIs while visible and active; reload restores groups',async()=>{
 const h=require(path),n=nodes(),calls=[];let shown=true,status='queued';
 const view=h.createStudies({nodes:n,el:(tag,text)=>new Element(tag,text),visible:()=>shown,api:async url=>{calls.push(url);return {items:[{id:'saved',status,training:[]}]};}});
 await view.open();assert.equal(calls.length,1);shown=false;await view.poll();assert.equal(calls.length,1);
 shown=true;await view.poll();assert.equal(calls.length,2);status='completed';await view.poll();await view.poll();assert.equal(calls.length,3);assert.ok(calls.every(url=>url==='/api/studies'));
 assert.match(all(n.list).map(x=>x.textContent||'').join(' '),/已完成/);
});
test('submission refresh waits for an older list read and preserves a newer form',async()=>{
 const h=require(path),n=nodes();let resolveList,resolvePost,listReads=0;
 const study={id:'new',status:'queued',training:[]};
 const view=h.createStudies({nodes:n,el:(tag,text)=>new Element(tag,text),visible:()=>true,api:async(url,body)=>{if(body)return new Promise(resolve=>{resolvePost=resolve;});listReads++;if(listReads===1)return new Promise(resolve=>{resolveList=resolve;});return {items:[study]};}});
 const loading=view.open();view.openForm(base);const first=n.form.children[0],inputs=all(first).filter(x=>x.tagName==='input');inputs[0].value='1,3';inputs[1].value='2024-07-01';const submitting=first.onsubmit({preventDefault(){}});
 view.openForm({...base,name:'另一个实验'});const newer=n.form.children[0];resolvePost(study);await Promise.resolve();await Promise.resolve();resolveList({items:[]});await Promise.all([loading,submitting]);
 assert.equal(listReads,2);assert.equal(n.form.children[0],newer);assert.match(all(n.list).map(x=>x.textContent||'').join(' '),/new/);
});
test('momentum grid parses bounded combinations and rejects unsupported strategies',()=>{
 const {parseStudy}=require(path),momentum={...base,request:{...base.request,strategy_id:'price_momentum'}};
 assert.deepEqual(parseStudy(momentum,'1,3','2024-07-01','10,20').lookbacks,[10,20]);
 assert.equal(parseStudy(momentum,'1,3','2024-07-01','').lookbacks,undefined);
 for(const windows of ['1,1','0,2','1.5,3','1,2,3,4,5,6,7,8,9'])assert.throws(()=>parseStudy(momentum,'1,3','2024-07-01',windows));
 assert.throws(()=>parseStudy(momentum,'1,2,3,4','2024-07-01','1,2,3,4,5,6,7'));
 assert.throws(()=>parseStudy(base,'1,3','2024-07-01','10,20'));
});
test('grid form previews count and submits both axes, result displays locked window',async()=>{
 const h=require(path),n=nodes(),calls=[];
 const b={...base,request:{...base.request,strategy_id:'qlib_momentum',parameters:{lookback:20}}};
 const study={id:'grid',status:'completed',training:[{holding_period_days:3,lookback:10,status:'succeeded',metrics:{trade_count:2,cumulative_return:.1}}],selected_holding_period_days:3,selected_candidate:{holding_period_days:3,lookback:10},validation:{holding_period_days:3,lookback:10,status:'succeeded'},request:b.request};
 const view=h.createStudies({nodes:n,el:(tag,text)=>new Element(tag,text),visible:()=>true,api:async(url,body)=>{calls.push([url,body]);return body?study:{items:[study]};}});
 view.openForm(b);const form=n.form.children[0],inputs=all(form).filter(e=>e.tagName==='input');
 inputs[0].value='1,3';inputs[1].value='2024-07-01';inputs[2].value='10,20';inputs[2].oninput();
 assert.match(all(form).map(e=>e.textContent||'').join(' '),/4 组前段回测/);
 await form.onsubmit({preventDefault(){}});
 assert.deepEqual(calls[0][1].lookbacks,[10,20]);
 assert.match(all(n.detail).map(e=>e.textContent||'').join(' '),/动量窗口 10 天/);
});
