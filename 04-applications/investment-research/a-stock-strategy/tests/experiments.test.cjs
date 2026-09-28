const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
class Element {
 addEventListener(type,handler){(this.listeners??={})[type]=handler;}
 dispatchEvent(event){this.listeners?.[event.type]?.(event);}
 constructor(tag){this.tagName=tag;this.children=[];this.dataset={};}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=items;}
 setAttribute(){}
}
function page(){
 const nodes={};const context=vm.createContext({document:{getElementById:id=>nodes[id]??=new Element('div'),createElement:tag=>new Element(tag)}});
 vm.runInContext(fs.readFileSync('src/strategy/interfaces/web/static/explanations.js','utf8'),context);
 vm.runInContext(fs.readFileSync('src/strategy/interfaces/web/static/app.js','utf8').replace('init().catch(e=>notice(e.message));',''),context);
 return {nodes,context,run:code=>vm.runInContext(code,context)};
}
function all(node){return [node,...node.children.flatMap(all)];}
test('experiment statuses preserve results and show IDs, retry and disabled behavior',async()=>{
 const {nodes,run}=page();
 run("state.experiments={enabled:true,ui_url:'http://127.0.0.1:5000'};renderExperiment($('detail'),{id:'abc',status:'succeeded',experiment:{status:'synced',run_id:'run123',experiment_id:'exp456'}})");
 assert.match(all(nodes.detail).map(n=>n.textContent||'').join(' '),/run123.*exp456/);
 for(const status of ['not_recorded','failed']){
  run(`$('detail').replaceChildren();renderExperiment($('detail'),{id:'abc',status:'succeeded',experiment:{status:'${status}',message:'同步失败'}})`);
  const button=all(nodes.detail).find(n=>n.tagName==='button');assert.ok(button);
  run("globalThis.calls=[];api=async(path,body)=>{calls.push([path,body]);return {};};refresh=async()=>{};showJob=async()=>{};");
  await button.onclick();assert.equal(run('calls[0][0]'),'/api/jobs/abc/experiment');assert.equal(run('JSON.stringify(calls[0][1])'),'{}');
 }
 for(const status of ['pending','disabled']){
  run(`$('detail').replaceChildren();renderExperiment($('detail'),{id:'abc',status:'succeeded',experiment:{status:'${status}'}})`);
  assert.equal(all(nodes.detail).some(n=>n.tagName==='button'),false);
 }
});
test('task history keeps sync status without a direct advanced link',()=>{
 const {nodes,run}=page();run("state.experiments={enabled:true,ui_url:'http://127.0.0.1:5000'};renderJobs()");
 assert.equal(all(nodes.jobs).some(n=>n.tagName==='a'),false);
 run('state.experiments.enabled=false;renderJobs()');assert.equal(all(nodes.jobs).some(n=>n.tagName==='a'),false);
 assert.equal(run("jobNeedsRefresh({status:'succeeded',experiment:{status:'pending'}})"),true);
 assert.equal(run("jobNeedsRefresh({status:'succeeded',experiment:{status:'synced'}})"),false);
});
test('detail invokes experiment panel and history includes sync state',async()=>{
 const {nodes,run}=page();
 run("state.experiments={enabled:true,ui_url:'http://127.0.0.1:5000'};globalThis.job={id:'abc',status:'succeeded',experiment:{status:'pending'}};api=async()=>job;state.jobs=[job];renderJobs()");
 assert.match(all(nodes.jobs).map(n=>n.textContent||'').join(' '),/实验同步中/);
 await run("showJob('abc')");
 assert.match(all(nodes.detail).map(n=>n.textContent||'').join(' '),/实验同步中/);
});
