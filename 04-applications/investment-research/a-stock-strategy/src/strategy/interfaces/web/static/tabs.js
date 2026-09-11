/* 只切换面板可见性，不重建表单；后台刷新不改变用户当前标签页。 */
(function(root){
  function createTabs(buttons,panels){
    const ids=buttons.map(b=>b.dataset.tab);
    function select(id,focus=false){
      if(!ids.includes(id))return false;
      for(const b of buttons){const active=b.dataset.tab===id;b.setAttribute('aria-selected',String(active));b.setAttribute('tabindex',active?'0':'-1');if(active&&focus)b.focus();}
      for(const p of panels)p.hidden=p.dataset.tab!==id;
      return true;
    }
    function keydown(id,event){
      const index=ids.indexOf(id),moves={ArrowRight:(index+1)%ids.length,ArrowLeft:(index+ids.length-1)%ids.length,Home:0,End:ids.length-1};
      if(!(event.key in moves))return;
      event.preventDefault();select(ids[moves[event.key]],true);
    }
    buttons.forEach(b=>{b.onclick=()=>select(b.dataset.tab);b.onkeydown=e=>keydown(b.dataset.tab,e);});
    select(ids[0]);return {select,keydown};
  }
  if(typeof module!=='undefined')module.exports={createTabs};
  if(typeof document!=='undefined'){
    const tabs=createTabs([...document.querySelectorAll('[role="tab"]')],[...document.querySelectorAll('[role="tabpanel"]')]);
    root.WorkbenchTabs=tabs;
    for(const link of document.querySelectorAll('[data-tab-target]'))link.onclick=e=>{e.preventDefault();tabs.select(link.dataset.tabTarget,true);};
  }
})(globalThis);
