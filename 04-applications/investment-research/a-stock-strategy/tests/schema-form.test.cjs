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
