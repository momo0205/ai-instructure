const {test}=require('node:test'),assert=require('node:assert/strict');
const {available,create}=require('../src/strategy/interfaces/web/static/compositions.js');
class E{constructor(tag,text){this.tagName=tag;this.textContent=text;this.children=[];this.value='';this.checked=false;}append(...n){this.children.push(...n);}replaceChildren(...n){this.children=n;}setAttribute(){}}
const all=n=>[n,...n.children.flatMap(all)];
const data=[{id:'real',name:'base',sample:false,instruments:[{symbol:'A',name:'A',backtest_supported:true}]},{id:'managed',name:'extra',instruments:[{symbol:'A',name:'A',backtest_supported:true},{symbol:'B',name:'B',backtest_supported:true}]},{id:'sample',sample:true,instruments:[{symbol:'C',backtest_supported:true}]}];
test('one entry per security and explicit source versions, excludes samples',()=>{const a=available(data);assert.equal(a.size,2);assert.equal(a.get('A').length,2);});
test('preview required, changed selection invalidates, successful publish exposes navigation',async()=>{
 const nodes=Object.fromEntries(['base','members','preview','status','check','publish','refresh'].map(k=>[k,new E('div')]));const calls=[];let opened;
 const view=create({nodes,el:(t,x)=>new E(t,x),onCreated:async id=>{opened=id;},api:async(url,payload)=>{calls.push([url,payload]);if(url==='/api/datasets')return data;return {members:payload.members,start:'2024-01-01',end:'2024-12-31',sessions:200,adjustment:'qfq',warnings:[],preview_digest:'hash',dataset_id:'managed_new'};}});
 await view.load();for(const row of nodes.members.children){const check=all(row).find(n=>n.tagName==='input'),select=all(row).find(n=>n.tagName==='select');check.checked=true;select.value='managed';check.onchange();}
 assert.equal(nodes.publish.disabled,true);await nodes.check.onclick();assert.equal(nodes.publish.disabled,false);await nodes.publish.onclick();assert.equal(calls.at(-1)[1].preview_digest,'hash');assert.equal(nodes.publish.disabled,true);
 await all(nodes.preview).find(n=>n.tagName==='button').onclick();assert.equal(opened,'managed_new');
});
