const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(){
 const nodes={};const state={datasets:[{id:'real',sample:false,instruments:[]}],snapshotJobId:null};const pending=[],copied=[];
 const ctx={state,$:id=>nodes[id]??=(id==='dataset'?{value:'real',replaceChildren(){}}:{}),api:()=>new Promise(resolve=>pending.push(resolve)),copyRequest:r=>copied.push(r),Option:class{},selectedSymbols:()=>[],strategyFields(){},globalThis:null};ctx.globalThis=ctx;
 vm.runInNewContext(fs.readFileSync('src/strategy/interfaces/web/static/research-inputs.js','utf8'),ctx);
 return {ctx,pending,copied,state};
}
test('late snapshot response cannot replace latest copy or changed base',async()=>{
 const {ctx,pending,copied,state}=setup(),view=ctx.ResearchInputs;
 const a=view.restore({snapshot_job_id:'a'}),b=view.restore({snapshot_job_id:'b'});
 pending[1]({id:'managed_input',instruments:[]});await b;pending[0]({id:'managed_input',instruments:[]});await a;
 assert.equal(copied.length,1);assert.equal(state.snapshotJobId,'b');assert.equal(state.datasets.at(-1).snapshotJobId,'b');
 const c=view.restore({snapshot_job_id:'c'});view.cancelRestore();pending[2]({id:'managed_input',instruments:[]});await c;assert.equal(copied.length,1);
});
