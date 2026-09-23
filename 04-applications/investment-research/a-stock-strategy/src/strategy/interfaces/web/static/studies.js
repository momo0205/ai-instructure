/* 批量研究使用本机 study 索引，与 MLflow 同步状态和轮询解耦。 */
(function(root){
  'use strict';
  const active=status=>['queued','selecting','validating'].includes(status);
  const labels={queued:'排队中',selecting:'前段筛选中',validating:'后段验证中',completed:'已完成',failed:'失败',cancelled:'已取消',interrupted:'已中断',no_candidate:'无合格候选',succeeded:'已完成',running:'运行中'};
  const supportsGrid=base=>['price_momentum','qlib_momentum'].includes(base.request?.strategy_id);
  function parseStudy(base,text,validationStart,windowText=''){
    const tokens=text.split(/[,，]/).map(x=>x.trim());
    if(tokens.length<2||tokens.length>8||tokens.some(x=>!/^\d+$/.test(x)))throw new Error('请填写 2 至 8 个不同的整数持有期，用逗号分隔。');
    const periods=tokens.map(Number);
    if(new Set(periods).size!==periods.length||periods.some(x=>x<1||x>252))throw new Error('持有期不能重复，且须在 1 至 252 天之间。');
    const parsed=new Date(validationStart);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(validationStart)||Number.isNaN(parsed.getTime())||parsed.toISOString().slice(0,10)!==validationStart||validationStart<=base.request.start||validationStart>base.request.end)throw new Error('后段开始日须晚于原回测开始日，且不晚于结束日。');
    const result={base_job_id:base.job_id,holding_periods:periods,validation_start:validationStart};
    if(windowText.trim()){
      const tokens=windowText.split(/[,，]/).map(x=>x.trim()),windows=tokens.map(Number);
      if(!supportsGrid(base)||tokens.length>8||tokens.some(x=>!/^\d+$/.test(x))||windows.some(x=>x<1||x>252)||new Set(windows).size!==windows.length)throw new Error('动量策略可填写 1 至 8 个不重复窗口（1—252），用逗号分隔。');
      if(windows.length*periods.length>24)throw new Error('参数网格最多 24 组，请减少持有期或动量窗口。');
      result.lookbacks=windows;
    }
    return result;
  }
  function createStudies({api,el,nodes,visible,showJob,activateTab}){
    let items=[],loaded=false,busy=false,selected=null,detail=null,detailRequest=0,reloadRequested=false;const refreshWaiters=[];
    const message=text=>{nodes.status.textContent=text;};
    const status=study=>labels[study.status]||study.status||'尚未开始';
    function metric(values,key){const value=values?.[key];if(value==null||!Number.isFinite(Number(value)))return '—';return ['cumulative_return','max_drawdown'].includes(key)?`${(Number(value)*100).toFixed(2)}%`:String(value);}
    function renderRuns(runs){
      const wrap=el('div',null,'scroll'),table=el('table'),head=el('thead'),tr=el('tr');for(const label of ['持有天数','动量窗口','状态','累计收益','最大回撤','完整交易笔数','回测'])tr.append(el('th',label));head.append(tr);table.append(head);
      const body=el('tbody');for(const run of runs){const row=el('tr');for(const value of [run.holding_period_days,run.lookback??detail?.request?.parameters?.lookback??'—',status(run),metric(run.metrics,'cumulative_return'),metric(run.metrics,'max_drawdown'),metric(run.metrics,'trade_count')])row.append(el('td',value));
        const cell=el('td');if(run.job_id){const button=el('button','查看回测详情');button.type='button';button.onclick=async()=>{try{await showJob(run.job_id);activateTab('research');}catch(error){message(`详情加载失败：${error.message}`);}};cell.append(button);}else cell.textContent='—';row.append(cell);body.append(row);
      }table.append(body);wrap.append(table);return wrap;
    }
    function renderDetail(){
      nodes.detail.replaceChildren();if(!detail)return;const study=detail;
      nodes.detail.append(el('h3',`批量验证 · ${status(study)}`),el('p',`组号：${study.id}`,'hint'));
      if(study.message)nodes.detail.append(el('p',study.message,'hint'));
      if(active(study.status)){const cancel=el('button','取消批量验证');cancel.type='button';cancel.onclick=async()=>{cancel.disabled=true;try{const updated=await api(`/api/studies/${encodeURIComponent(study.id)}/cancel`,{});if(selected===study.id){detail=updated;renderDetail();}await load(true);}catch(error){message(`取消失败：${error.message}`);cancel.disabled=false;}};nodes.detail.append(cancel);}
      nodes.detail.append(el('h4','前段筛选'),el('p',`${study.selection_start||'—'} — ${study.selection_end||'—'}`,'hint'),renderRuns(study.training||[]));
      nodes.detail.append(el('p',study.selected_holding_period_days!=null?`选定持有期：${study.selected_holding_period_days} 天${study.selected_candidate?.lookback!=null?`，动量窗口 ${study.selected_candidate.lookback} 天`:''}。按前段累计收益最高且至少 1 笔完整交易筛选；同收益先选较短持有期，再选较短动量窗口。`:'尚未选定候选。只有至少完成 1 笔交易的候选才参与收益排序。','hint'));
      nodes.detail.append(el('h4','后段验证'),el('p',`${study.validation_start||'—'} — ${study.validation_end||'—'}；独立初始资金，不继承前段持仓。`,'hint'));
      if(study.validation)nodes.detail.append(renderRuns([study.validation]));else nodes.detail.append(el('p',study.status==='no_candidate'?'前段没有合格候选，未运行后段验证。':'后段仅验证前段选出的一个持有期，结果尚未产生。','hint'));
      nodes.detail.append(el('p','本批量不运行 100 轮随机对照。后段不参与本轮自动选参；若此前已看过该区间结果，或反复用它调参，就不算严格的未见数据验证。','hint'));
    }
    function renderList(){
      nodes.list.replaceChildren();if(!items.length){nodes.list.append(el('p','暂无批量验证。可在上方实验列表选择“批量验证”。','hint'));return;}
      for(const study of items){const button=el('button',`${status(study)} · 持有期 ${(study.holding_periods||[]).join('、')||'—'} 天${study.lookbacks?.length?` × 窗口 ${study.lookbacks.join('、')} 天`:''} · ${study.id}`,'study-group');button.type='button';button.onclick=()=>select(study.id);nodes.list.append(button);}
    }
    async function select(id){
      selected=id;const token=++detailRequest;message('正在加载批量验证详情…');
      try{const result=await api(`/api/studies/${encodeURIComponent(id)}`);if(token!==detailRequest||selected!==id)return;detail=result;renderDetail();message('');}
      catch(error){if(token===detailRequest)message(`批量详情加载失败：${error.message}`);}
    }
    async function load(force=false){
      if(busy){
        if(force)return new Promise(resolve=>{reloadRequested=true;refreshWaiters.push(resolve);});
        return;
      }busy=true;nodes.refresh.disabled=true;
      try{
        const result=await api('/api/studies');items=result.items||[];loaded=true;renderList();
        const summary=items.find(i=>i.id===selected);
        if(summary){
          // Summaries can contain compact result rows. Otherwise retrieve only the open group.
          if(Array.isArray(summary.training)){detail=summary;renderDetail();}
          else await select(selected);
        }
        message('');
      }catch(error){message(`批量验证加载失败：${error.message}。请点击刷新重试。`);}
      finally{
        busy=false;nodes.refresh.disabled=false;
        if(reloadRequested){reloadRequested=false;const waiting=refreshWaiters.splice(0);await load();waiting.forEach(resolve=>resolve());}
      }
    }
    function openForm(base){
      const form=el('form',null,'experiment-editor'),periods=el('input'),split=el('input'),windows=el('input');periods.type='text';periods.value='1,3,5';periods.required=true;
      split.type='date';split.required=true;split.max=base.request.end;
      const first=new Date(`${base.request.start}T00:00:00Z`);first.setUTCDate(first.getUTCDate()+1);split.min=first.toISOString().slice(0,10);
      const midpoint=new Date((Date.parse(base.request.start)+Date.parse(base.request.end))/2);split.value=midpoint.toISOString().slice(0,10);
      form.append(el('h3',`批量验证：${base.name||'所选实验'}`),el('p',`原回测区间：${base.request.start} — ${base.request.end}`,'hint'));
      for(const [title,input] of [['候选持有期（2 至 8 个，逗号分隔）',periods],['后段开始日',split]]){const label=el('label',title);label.append(input);form.append(label);}
      if(supportsGrid(base)){
        windows.type='text';windows.value=String(base.request.parameters?.lookback||20);
        const label=el('label','动量窗口（可选，逗号分隔；留空沿用原值）');label.append(windows);form.append(label);
        form.append(el('p','例如窗口 10,20,60 × 持有期 1,3,5，共 9 组。当前仅支持窗口与持有期两维，最多 24 组。Qlib 每组会独立计算因子。','hint'));
      }
      const estimate=el('p','','hint');form.append(estimate);
      function updateEstimate(){try{const request=parseStudy(base,periods.value,split.value,windows.value);const count=request.holding_periods.length*(request.lookbacks?.length||1);estimate.textContent=`将运行 ${count} 组前段回测；有合格候选后，再运行 1 次后段验证。`;}catch(error){estimate.textContent=error.message;}}
      periods.oninput=windows.oninput=split.oninput=updateEstimate;updateEstimate();
      form.append(el('p','前段按累计收益最高且至少 1 笔完整交易选出一个候选；同收益先选较短持有期，再选较短动量窗口。后段只验证选定参数，独立初始资金，不继承持仓。','hint'),el('p','批量不运行 100 轮随机对照。重复使用后段调参会削弱独立性。','hint'));
      const submit=el('button','开始批量验证');submit.type='submit';const close=el('button','关闭');close.type='button';close.onclick=()=>nodes.form.replaceChildren();form.append(submit,close);
      form.onsubmit=async event=>{event.preventDefault();if(submit.disabled)return;
        try{const request=parseStudy(base,periods.value,split.value,windows.value);submit.disabled=true;periods.disabled=true;split.disabled=true;windows.disabled=true;const study=await api('/api/studies',request);selected=study.id;detailRequest++;detail=study;renderDetail();if(nodes.form.children[0]===form)nodes.form.replaceChildren();await load(true);}
        catch(error){message(`批量验证未提交：${error.message}`);submit.disabled=false;periods.disabled=false;split.disabled=false;windows.disabled=false;}
      };nodes.form.replaceChildren(form);nodes.form.scrollIntoView({behavior:'smooth',block:'start'});periods.focus();
    }
    nodes.refresh.onclick=()=>load(true);
    return {openForm,load,open:()=>{if(!loaded)return load();},poll:()=>{if(visible()&&items.some(study=>active(study.status)))return load();},select};
  }
  if(typeof module!=='undefined')module.exports={parseStudy,active,createStudies};
  if(typeof document!=='undefined'){
    const panel=document.getElementById('panel-experiments');if(!panel)return;
    const nodes=Object.fromEntries(['status','form','list','detail','refresh'].map(key=>[key,document.getElementById(`studies-${key}`)]));
    const view=createStudies({api,el,nodes,visible:()=>!panel.hidden,showJob,activateTab});root.StudiesWorkbench=view;
    new MutationObserver(()=>{if(!panel.hidden)view.open();}).observe(panel,{attributes:true,attributeFilter:['hidden']});
    if(!panel.hidden)view.open();
    setInterval(()=>view.poll(),2000);
  }
})(globalThis);
