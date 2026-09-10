const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
class Element {
  constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.value='';this.checked=false;}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=children;}
  get selectedOptions(){return this.children.filter(c=>c.selected);}
  querySelectorAll(){return this.children.flatMap(c=>[...(c.dataset.parameter?[c]:[]),...c.querySelectorAll()]);}
  querySelector(){return this.querySelectorAll().find(c=>['symbol','candidate_symbols'].includes(c.dataset.parameter));}
  scrollIntoView(){}
}
function page(){
 const nodes={}; const context=vm.createContext({document:{getElementById:id=>nodes[id]??=new Element('div'),createElement:tag=>new Element(tag)},Option:class extends Element{constructor(label,value){super('option');this.textContent=label;this.value=value;}},InstrumentChoices:require('../src/strategy/interfaces/web/static/instrument-options.js'),setInterval(){}});
 let source=fs.readFileSync('src/strategy/interfaces/web/static/app.js','utf8');
 vm.runInContext(source.replace('init().catch(e=>notice(e.message));',''),context);
 vm.runInContext(`state.datasets=[{id:'sample',start:'2024-01-01',end:'2024-12-31',instruments:[{symbol:'X',backtest_supported:true,start:'2024-01-01',end:'2024-12-31'}]}];state.strategies=[{id:'third',parameters:[{name:'assets',type:'array',role:'instrument',default:['X']},{name:'enabled',type:'boolean',default:true},{name:'style',type:'string',options:['fast','slow'],default:'fast'},{name:'limits',type:'object',default:{a:2}},{name:'levels',type:'array',default:[1,2]},{name:'history',type:'integer',default:3}]}];$('strategy').value='third';$('dataset').value='sample';strategyFields();`,context);
 return {nodes,context,run:code=>JSON.parse(JSON.stringify(vm.runInContext(code,context)))};
}
test('arbitrary schema fields render, submit typed values and copy false',()=>{
 const {nodes,run}=page();const controls=Object.fromEntries(nodes['strategy-parameters'].querySelectorAll().map(c=>[c.dataset.parameter,c]));
 assert.equal(controls.assets.tagName,'select');assert.equal(controls.assets.multiple,true);
 assert.equal(controls.enabled.type,'checkbox');assert.equal(controls.enabled.required,false);
 controls.enabled.checked=false;controls.style.value='slow';controls.history.value='7';
 const request=run('requestFromForm()');
 assert.deepEqual(request.parameters,{assets:['X'],enabled:false,style:'slow',limits:{a:2},levels:[1,2],history:7});assert.deepEqual(run('selectedSymbols()'),['X']);
 run(`copyRequest(${JSON.stringify(request)}); null`);
 assert.equal(nodes['strategy-parameters'].querySelectorAll().find(c=>c.dataset.parameter==='enabled').checked,false);
 assert.deepEqual(run('requestFromForm().parameters'),request.parameters);
});
test('missing instrument role reports the contract instead of guessing field names',()=>{
 const {nodes,run}=page();run("state.strategies[0].parameters=[{name:'symbol',type:'string',default:'X'}];strategyFields();null");
 assert.equal(nodes.submit.disabled,true);assert.match(nodes['coverage-info'].textContent,/未配置页面标的选择/);
});
test('single and multiple instrument roles aggregate without parameter-name assumptions',()=>{
 const {nodes,run}=page();
 run("state.strategies[0].parameters.push({name:'benchmark',role:'instrument',type:'string',default:'X'},{name:'threshold',type:'number',enum:[0.5,1.5],default:0.5},{name:'note',type:'string',default:'hello'});strategyFields();null");
 const controls=Object.fromEntries(nodes['strategy-parameters'].querySelectorAll().map(c=>[c.dataset.parameter,c]));
 assert.equal(controls.benchmark.multiple,false);controls.benchmark.value='X';controls.threshold.value='1.5';
 assert.deepEqual(run('selectedSymbols()'),['X']);assert.equal(run('requestFromForm().parameters.threshold'),1.5);assert.equal(run('requestFromForm().parameters.note'),'hello');
 controls.levels.value='{}';assert.throws(()=>run('requestFromForm()'),/levels.*array/);
});

test('zero-trade result explains insufficient cash before metrics, without treating an open position as no entry',()=>{
 const {run}=page();
 const events=Array.from({length:37},()=>({side:'buy',status:'cancelled',reason:'insufficient_cash'}));
 const result={trades:[],execution_events:events};
 assert.match(run(`noTradeMessage(${JSON.stringify(result)})`),/37.*资金不足/);
 assert.match(run(`noTradeMessage(${JSON.stringify(result)})`),/初始资金/);
 assert.match(run(`noTradeMessage(${JSON.stringify({...result,execution_events:[...events,{side:'buy',status:'filled'}]})})`),/尚未完成卖出/);
 assert.equal(run('noTradeMessage({trades:[{}]})'),'');
 assert.match(run('noTradeMessage({trades:[],execution_events:[]})'),/触发条件/);
});

test('structured diagnostic shows code, action and budget evidence',()=>{
 const {run}=page();
 const text=run(`diagnosticText({code:'INSUFFICIENT_CASH',message:'资金不足',action:'调整模拟资金',context:{count:37,available_cash:100000,minimum_required_cash:150000}})`);
 assert.match(text,/INSUFFICIENT_CASH/);assert.match(text,/调整模拟资金/);assert.match(text,/150,000/);
});

test('API connection failure is actionable in Chinese',async()=>{
 const {context}=page();context.fetch=async()=>{throw new TypeError('Failed to fetch');};
 await assert.rejects(vm.runInContext("api('/api/jobs')",context),/NETWORK_ERROR.*本地服务/);
});
