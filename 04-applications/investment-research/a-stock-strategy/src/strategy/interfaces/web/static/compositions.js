/* 组合研究数据集：每只证券显式选择一个版本，先检查再发布。 */
(function(root){
  'use strict';
  function available(datasets){
    const result=new Map();
    for(const dataset of datasets.filter(d=>!d.sample))for(const item of dataset.instruments||[]){
      if(!item.backtest_supported)continue;
      if(!result.has(item.symbol))result.set(item.symbol,[]);
      result.get(item.symbol).push({dataset,item});
    }
    return result;
  }
  function create({api,el,nodes,onCreated}){
    let controls=[],preview=null,busy=false;
    const invalidate=()=>{preview=null;nodes.publish.disabled=true;nodes.preview.replaceChildren();};
    function request(){return {base_dataset_id:nodes.base.value,members:controls.filter(c=>c.check.checked).map(c=>({symbol:c.symbol,dataset_id:c.select.value}))};}
    async function load(){
      if(busy)return;busy=true;nodes.refresh.disabled=true;
      const previous=request();
      try{
        const datasets=await api('/api/datasets');invalidate();nodes.base.replaceChildren();
        for(const dataset of datasets.filter(d=>!d.sample)){const option=el('option',dataset.name);option.value=dataset.id;nodes.base.append(option);}
        if(datasets.some(d=>d.id===previous.base_dataset_id&&!d.sample))nodes.base.value=previous.base_dataset_id;
        else nodes.base.value=datasets.some(d=>d.id==='real')?'real':datasets.find(d=>!d.sample)?.id||'';
        controls=[];nodes.members.replaceChildren();
        for(const [symbol,versions] of available(datasets)){
          const row=el('div',null,'composition-row'),check=el('input'),select=el('select');check.type='checkbox';
          const label=el('label',`${versions[0].item.name} · ${symbol}`);check.setAttribute('aria-label',`选择 ${symbol}`);label.append(check);row.append(label);
          select.setAttribute('aria-label',`${symbol} 来源版本`);
          for(const {dataset,item} of versions){const option=el('option',`${dataset.name} · ${item.start} — ${item.end}`);option.value=dataset.id;select.append(option);}
          const old=previous.members.find(m=>m.symbol===symbol);if(old&&versions.some(v=>v.dataset.id===old.dataset_id)){check.checked=true;select.value=old.dataset_id;}
          check.onchange=select.onchange=invalidate;row.append(select);nodes.members.append(row);controls.push({symbol,check,select});
        }
        nodes.check.disabled=controls.length<2;nodes.status.textContent=controls.length<2?'需要至少两只已准备的真实证券。':'勾选证券，并为每只选择一个来源版本。';
      }catch(error){nodes.status.textContent=`目录加载失败：${error.message}`;}finally{busy=false;nodes.refresh.disabled=false;}
    }
    nodes.base.onchange=invalidate;nodes.refresh.onclick=load;
    nodes.check.onclick=async()=>{
      if(busy)return;const payload=request();invalidate();busy=true;nodes.check.disabled=true;nodes.status.textContent='正在检查共同区间与数据兼容性…';
      try{const result=await api('/api/compositions/preview',payload);
        // 用户等待期间改了选择，不能把旧检查结果用于新请求。
        if(JSON.stringify(payload)!==JSON.stringify(request())){nodes.status.textContent='选择已变化，请重新检查组合。';return;}
        preview={payload,result};nodes.preview.append(el('p',`${result.members.length} 只证券 · ${result.start} — ${result.end} · ${result.sessions} 个交易日 · 复权 ${result.adjustment}`));
        for(const member of result.members)nodes.preview.append(el('p',`${member.symbol} ← ${member.dataset_id}`,'hint'));
        const notes=el('details');notes.append(el('summary','组合来源与限制'));for(const warning of result.warnings)notes.append(el('p',warning,'hint'));nodes.preview.append(notes);
        nodes.publish.disabled=false;nodes.status.textContent='检查通过。创建后会新增独立版本，不会下载或自动回测。';
      }catch(error){nodes.status.textContent=`无法组合：${error.message}`;}finally{busy=false;nodes.check.disabled=false;}
    };
    nodes.publish.onclick=async()=>{
      if(busy||!preview)return;const checked=preview;busy=true;nodes.publish.disabled=true;nodes.check.disabled=true;nodes.status.textContent='正在创建组合版本…';
      try{const result=await api('/api/compositions',{...checked.payload,preview_digest:checked.result.preview_digest});preview=null;
        nodes.status.textContent=`组合已创建：${result.dataset_id}。可使用该版本进行多标的回测。`;
        const use=el('button','使用组合数据回测');use.type='button';use.onclick=()=>onCreated(result.dataset_id).catch(error=>{nodes.status.textContent=`组合已创建，但打开失败：${error.message}。请刷新数据目录后选择该版本。`;});nodes.preview.append(use);
      }catch(error){preview=null;nodes.status.textContent=`创建未完成：${error.message}。请重新检查组合。`;}finally{busy=false;nodes.check.disabled=false;}
    };
    return {load};
  }
  if(typeof module!=='undefined')module.exports={available,create};
  if(typeof document!=='undefined'){
    const panel=document.getElementById('panel-data');if(!panel)return;
    const nodes=Object.fromEntries(['base','members','preview','status','check','publish','refresh'].map(k=>[k,document.getElementById(`composition-${k}`)]));
    const view=create({api,el,nodes,onCreated:async id=>{await refreshData();$('dataset').value=id;datasetFields();strategyFields();configurePanel(true);activateTab('research');}});
    new MutationObserver(()=>{if(!panel.hidden)view.load();}).observe(panel,{attributes:true,attributeFilter:['hidden']});
    if(!panel.hidden)view.load();root.Compositions=view;
  }
})(globalThis);
