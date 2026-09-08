const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
// 执行页面真实刷新函数，用延迟响应复现下载发布与用户切换之间的竞态。
const source=fs.readFileSync(require('node:path').join(__dirname,'../src/strategy/static/app.js'),'utf8');
const refresh=source.slice(source.indexOf('async function refreshData()'),source.indexOf("$('refresh-data').onclick"));
test('refresh reads downloads before datasets and preserves selection made during request',async()=>{
  let release;
  const gate=new Promise(resolve=>{release=resolve;});
  const calls=[];
  const nodes={dataset:{value:'real',replaceChildren(){this.value='real';}}};
  const context={state:{},$:id=>nodes[id]??={replaceChildren(){},value:''},
    Option:function(name,id){this.value=id;},el:()=>({}),table:()=>({}),
    datasetFields(){throw new Error('must preserve selected dataset');},strategyFields(){},renderDownloads(){},
    api:async path=>{calls.push(path);if(path==='/api/downloads'){await gate;return [{status:'succeeded',dataset_id:'managed_new'}];}
      return [{id:'real',name:'real',start:'2024-01-01',end:'2024-12-31'}, {id:'managed_new',name:'new'}];},
  };
  vm.createContext(context);vm.runInContext(refresh,context);
  const pending=context.refreshData();
  assert.deepEqual(calls,['/api/downloads']);
  nodes.dataset.value='managed_new';release();await pending;
  assert.deepEqual(calls,['/api/downloads','/api/datasets']);
  assert.equal(nodes.dataset.value,'managed_new');
});
