/* 真实行情直接跨版本选证券；数据集选择器在此模式下只决定指数/广度基线。 */
(function(root){
  'use strict';
  const choices=new Map();
  let restoreGeneration=0;
  const cancelRestore=()=>{restoreGeneration++;};
  function enabled(){return !!$('cross-version')?.checked&&!state.snapshotJobId&&!state.datasets.find(d=>d.id===$('dataset').value)?.sample;}
  function instruments(){
    const map=new Map();for(const d of state.datasets.filter(d=>!d.sample&&!d.taskSnapshot))for(const i of d.instruments||[])if(i.backtest_supported&&!map.has(i.symbol))map.set(i.symbol,i);
    return [...map.values()];
  }
  function sources(){
    const nodes=$('research-sources');if(!nodes)return;
    nodes.replaceChildren();$('cross-version').disabled=!!state.snapshotJobId||!!state.datasets.find(d=>d.id===$('dataset').value)?.sample;
    $('research-input-hint').textContent=state.snapshotJobId?'正在复用原任务冻结行情；修改参数后直接重跑。切换历史数据/基线可重新选择来源。':enabled()?'跨版本选择证券；上方数据集作为指数/广度基线。提交时自动检查兼容性并冻结到任务，不创建全局组合版本。':'使用所选数据集中的证券。';
    if(!enabled())return;
    for(const symbol of selectedSymbols()){
      const versions=state.datasets.filter(d=>!d.sample&&!d.taskSnapshot&&d.instruments.some(i=>i.symbol===symbol&&i.backtest_supported));
      const select=el('select');select.setAttribute('aria-label',`${symbol} 研究来源版本`);
      for(const d of versions)select.append(new Option(d.name,d.id));
      const prior=choices.get(symbol);select.value=versions.some(d=>d.id===prior)?prior:versions.some(d=>d.id===$('dataset').value)?$('dataset').value:versions[0]?.id||'';
      choices.set(symbol,select.value);
      select.onchange=()=>{choices.set(symbol,select.value);updateCoverage();};
      const label=el('label',`${symbol} 来源版本`);label.append(select);nodes.append(label);
    }
  }
  function selection(){return {base_dataset_id:$('dataset').value,members:selectedSymbols().map(symbol=>({symbol,dataset_id:choices.get(symbol)}))};}
  function dataset(){
    const base=state.datasets.find(d=>d.id===$('dataset').value);if(!enabled())return base;
    return {...base,instruments:selectedSymbols().map(symbol=>state.datasets.find(d=>d.id===choices.get(symbol))?.instruments.find(i=>i.symbol===symbol)).filter(Boolean)};
  }
  async function submit(request){
    if(enabled())return api('/api/jobs/from-selection',{request,selection:selection()});
    return api('/api/jobs',request);
  }
  async function restore(request){
    const generation=++restoreGeneration;
    const entry=await api(`/api/jobs/${encodeURIComponent(request.snapshot_job_id)}/input-dataset`);
    if(generation!==restoreGeneration)return;
    state.datasets=state.datasets.filter(d=>d.id!==entry.id);state.datasets.push({...entry,taskSnapshot:true,snapshotJobId:request.snapshot_job_id});
    $('dataset').replaceChildren(...state.datasets.map(d=>new Option(d.name,d.id)));
    state.snapshotJobId=request.snapshot_job_id;copyRequest(request,true);
  }
  root.ResearchInputs={enabled,instruments,sources,dataset,submit,restore,cancelRestore};
  $('cross-version').onchange=()=>{state.snapshotJobId=null;strategyFields();};
})(globalThis);
