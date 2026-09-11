const {test}=require('node:test');const assert=require('node:assert/strict');
const {createTabs}=require('../src/strategy/interfaces/web/static/tabs.js');
function fixture(){
 const make=id=>({dataset:{tab:id},attrs:{},hidden:false,setAttribute(k,v){this.attrs[k]=v;},focus(){this.focused=true;}});
 const buttons=['research','history','data'].map(make),panels=buttons.map(b=>({...make(b.dataset.tab),value:'未提交参数'}));
 return {buttons,panels,tabs:createTabs(buttons,panels)};
}
test('tabs preserve panels and synchronize selection, visibility and focus',()=>{
 const {buttons,panels,tabs}=fixture();tabs.select('history');
 assert.equal(panels[0].hidden,true);assert.equal(panels[1].hidden,false);assert.equal(panels[0].value,'未提交参数');
 assert.equal(buttons[1].attrs['aria-selected'],'true');assert.equal(buttons[0].attrs.tabindex,'-1');
 tabs.keydown('history',{key:'ArrowRight',preventDefault(){}});assert.equal(panels[2].hidden,false);assert.equal(buttons[2].focused,true);
 tabs.keydown('data',{key:'Home',preventDefault(){}});assert.equal(panels[0].hidden,false);
 assert.equal(tabs.select('invalid'),false);assert.equal(panels[0].hidden,false);
});
