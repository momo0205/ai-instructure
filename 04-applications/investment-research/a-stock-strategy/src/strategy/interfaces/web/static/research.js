/* 中文实验研究页：只按需读实验索引；回测执行与参数复制继续使用原页面入口。 */
(function(root){
  'use strict';
  const percentKeys=new Set(['cumulative_return','max_drawdown','win_rate','annualized_return','buy_hold_return','random_median_return','random_percentile']);
  function metric(values,key){
    const value=values?.[key];
    if(value==null||!Number.isFinite(Number(value))||(key==='win_rate'&&!values.trade_count))return '—';
    if(key==='random_percentile')return `第 ${Number(value).toFixed(2)} 百分位`;
    return percentKeys.has(key)?`${(Number(value)*100).toFixed(2)}%`:String(value);
  }
  function stable(value){
    if(Array.isArray(value))return `[${value.map(stable).join(',')}]`;
    if(value&&typeof value==='object')return `{${Object.keys(value).sort().map(k=>`${JSON.stringify(k)}:${stable(value[k])}`).join(',')}}`;
    return JSON.stringify(value);
  }
  function changedParameters(items){
    const keys=[...new Set(items.flatMap(item=>Object.keys(item.request?.parameters||{})))];
    return keys.filter(key=>new Set(items.map(item=>stable(item.request?.parameters?.[key]))).size>1);
  }
  function comparisonWarnings(items){
    if(items.length<2)return [];
    const fields=[['回测区间',i=>[i.request?.start,i.request?.end]],['数据版本',i=>[i.data_version,i.request?.dataset_id]],['初始资金',i=>i.request?.initial_cash],['交易成本',i=>[i.request?.commission_rate,i.request?.minimum_commission,i.request?.slippage_bps]],['源码版本',i=>i.source_snapshot],['策略或版本',i=>[i.request?.strategy_id,i.strategy_version]]];
    const warnings=fields.filter(([,value])=>new Set(items.map(i=>stable(value(i)))).size>1).map(([label])=>`${label}不同，指标不能直接归因于参数调整。`);
    if(items.some(i=>!i.data_version||i.data_version==='unknown'))warnings.push('旧记录数据版本缺失，无法确认实验是否可比。');
    return warnings;
  }
  function matches(item,query){return stable([item.name,item.notes,item.request]).toLowerCase().includes(query.trim().toLowerCase());}
  function toggleSelection(selected,id,checked){if(checked&&selected.size>=4&&!selected.has(id))return false;checked?selected.add(id):selected.delete(id);return true;}
  function createResearch({api,el,nodes,strategyName,strategies,showJob,copyRequest,activateTab,beginStudy}){
    let items=[],loaded=false,loading=false;const selected=new Set(),loadWaiters=[];
    const message=text=>{nodes.status.textContent=text;};
    function symbols(item){
      const schema=strategies().find(s=>s.id===item.request?.strategy_id)?.parameters||[];
      const values=schema.filter(p=>p.role==='instrument').flatMap(p=>item.request?.parameters?.[p.name]||[]);
      return [...new Set(values)].join('、')||'—';
    }
    function datasetLabel(item){return item.request?.dataset_id==='mvp_sample'?'合成样例':item.request?.dataset_id||'未标明数据集';}
    function title(item){return item.name||`${strategyName(item.request?.strategy_id)} · ${symbols(item)} · 持有 ${item.request?.holding_period_days??'—'} 天`;}
    function grid(headers,rows){
      const wrap=el('div',null,'scroll'),t=el('table'),head=el('thead'),tr=el('tr');headers.forEach(h=>tr.append(el('th',h)));head.append(tr);t.append(head);
      const body=el('tbody');for(const row of rows){const r=el('tr');for(const value of row){const cell=el('td');if(value&&typeof value==='object'&&value.tagName)cell.append(value);else cell.textContent=value??'—';r.append(cell);}body.append(r);}t.append(body);wrap.append(t);return wrap;
    }
    function openEditor(item){
      const form=el('form',null,'experiment-editor'),name=el('input'),notes=el('textarea');
      name.value=title(item);name.required=true;name.maxLength=120;notes.value=item.notes||'';notes.maxLength=2000;
      for(const [title,input] of [['实验名称',name],['备注',notes]]){const label=el('label',title);label.append(input);form.append(label);}
      const save=el('button','保存名称和备注');save.type='submit';const close=el('button','取消');close.type='button';close.onclick=()=>nodes.editor.replaceChildren();form.append(save,close);
      form.onsubmit=async event=>{event.preventDefault();if(!name.value.trim()){message('请填写实验名称。');return;}save.disabled=true;name.disabled=true;notes.disabled=true;
        try{await api(`/api/jobs/${encodeURIComponent(item.job_id)}/experiment-label`,{name:name.value.trim(),notes:notes.value});
          // 旧请求不能关闭后来打开的另一条实验编辑表单。
          if(nodes.editor.children[0]===form)nodes.editor.replaceChildren();await load(true);}
        catch(error){message(`保存失败：${error.message}`);save.disabled=false;name.disabled=false;notes.disabled=false;}
      };nodes.editor.replaceChildren(form);name.focus();
    }
    function renderComparison(){
      const chosen=items.filter(i=>selected.has(i.job_id));nodes.comparison.replaceChildren();
      nodes.comparison.append(el('h3',`实验比较（${chosen.length}/4）`));
      if(chosen.length<2){nodes.comparison.append(el('p','勾选 2 至 4 条实验，查看指标和参数变化。','hint'));return;}
      for(const warning of comparisonWarnings(chosen))nodes.comparison.append(el('p',warning,'warnings'));
      const rows=[['策略',...chosen.map(i=>strategyName(i.request?.strategy_id))],['标的',...chosen.map(symbols)],['区间',...chosen.map(i=>`${i.request?.start||'—'} — ${i.request?.end||'—'}`)],['数据集',...chosen.map(datasetLabel)],['数据版本',...chosen.map(i=>{const v=el('span',i.data_version?i.data_version.slice(0,12):'未记录');v.title=i.data_version||'';return v;})],['初始资金',...chosen.map(i=>i.request?.initial_cash)]];
      for(const [label,key] of [['累计收益','cumulative_return'],['最大回撤','max_drawdown'],['完整交易笔数','trade_count'],['胜率','win_rate']])rows.push([label,...chosen.map(i=>metric(i.metrics,key))]);
      for(const [label,key] of [['买入持有收益','buy_hold_return'],['随机择时中位收益','random_median_return'],['策略随机百分位','random_percentile']])rows.push([label,...chosen.map(i=>metric(i.controls,key))]);
      const changed=changedParameters(chosen),keys=[...new Set(chosen.flatMap(i=>Object.keys(i.request?.parameters||{})))];
      for(const key of keys){const label=el('span',`${changed.includes(key)?'变化 · ':''}${parameterLabel(chosen[0],key)}`,changed.includes(key)?'parameter-changed':'');rows.push([label,...chosen.map(i=>stable(i.request?.parameters?.[key])??'—')]);}
      for(const [label,key] of [['持有天数','holding_period_days'],['下跌家数阈值','min_declining_count'],['指数跌幅阈值','trigger_return_threshold'],['佣金比例','commission_rate'],['最低佣金','minimum_commission'],['滑点（基点）','slippage_bps']]){
        const values=chosen.map(i=>i.request?.[key]);const changed=new Set(values.map(stable)).size>1;
        rows.push([el('span',`${changed?'变化 · ':''}${label}`,changed?'parameter-changed':''),...values.map(value=>['trigger_return_threshold','commission_rate'].includes(key)?metric({cumulative_return:value},'cumulative_return'):value)]);
      }
      nodes.comparison.append(grid(['指标 / 参数',...chosen.map(title)],rows));
    }
    function parameterLabel(item,key){return strategies().find(s=>s.id===item.request?.strategy_id)?.parameters.find(p=>p.name===key)?.label||key;}
    function render(){
      const visible=items.filter(i=>matches({...i,name:title(i)},nodes.filter.value||'')&&(!nodes.strategy.value||i.request?.strategy_id===nodes.strategy.value));
      nodes.list.replaceChildren();
      if(!visible.length)nodes.list.append(el('p',items.length?'没有符合筛选条件的实验。':'暂无已同步实验。请到任务历史将已完成回测同步到实验库，再刷新此页。','hint'));
      else nodes.list.append(grid(['比较','名称 / 备注','策略 / 标的','回测区间','累计收益','最大回撤','操作'],visible.map(item=>{
        const check=el('input');check.type='checkbox';check.checked=selected.has(item.job_id);check.setAttribute('aria-label',`比较 ${title(item)}`);
        check.onchange=()=>{if(!toggleSelection(selected,item.job_id,check.checked)){check.checked=false;message('最多同时比较 4 条实验。');}else message('');renderComparison();};
        const nameCell=el('div');nameCell.append(el('strong',title(item)),el('p',item.notes||'无备注','hint'));
        nameCell.append(el('p',`${datasetLabel(item)} · ${item.created_at&&!Number.isNaN(Date.parse(item.created_at))?new Date(item.created_at).toLocaleString('zh-CN'):'时间未记录'}`,'hint'));
        const actions=el('div',null,'experiment-row-actions');
        for(const [label,action] of [['查看详情',async()=>{await showJob(item.job_id);activateTab('research');}],['复制重跑',()=>copyRequest(item.request)],['编辑',()=>openEditor(item)],['批量验证',()=>beginStudy(item)]]){const button=el('button',label);button.type='button';button.onclick=async()=>{try{await action();}catch(error){message(`操作失败：${error.message}`);}};actions.append(button);}
        return [check,nameCell,`${strategyName(item.request?.strategy_id)} / ${symbols(item)}`,`${item.request?.start||'—'} — ${item.request?.end||'—'}`,metric(item.metrics,'cumulative_return'),metric(item.metrics,'max_drawdown'),actions];
      })));
      renderComparison();
    }
    async function load(afterPending=false){
      if(loading){
        // 保存完成时若旧查询尚在路上，等它结束后再读，避免显示保存前的名称。
        if(afterPending===true){await new Promise(resolve=>loadWaiters.push(resolve));return load(true);}return;
      }
      loading=true;nodes.refresh.disabled=true;message('正在加载实验…');
      try{
        const [result,settings]=await Promise.all([api('/api/research-experiments'),api('/api/experiments')]);items=result.items||[];loaded=true;
        for(const id of selected)if(!items.some(i=>i.job_id===id))selected.delete(id);
        const old=nodes.strategy.value;nodes.strategy.replaceChildren();const any=el('option','全部策略');any.value='';nodes.strategy.append(any);
        for(const id of new Set(items.map(i=>i.request?.strategy_id).filter(Boolean))){const option=el('option',strategyName(id));option.value=id;nodes.strategy.append(option);}nodes.strategy.value=old||'';
        nodes.advanced.replaceChildren();if(settings.enabled&&settings.ui_url){const details=el('details'),link=el('a','打开 MLflow 原始实验页面');link.href=settings.ui_url;link.target='_blank';link.rel='noopener noreferrer';details.append(el('summary','高级工具'),link);nodes.advanced.append(details);}
        render();message(result.enabled?`最近 ${items.length} 条实验（最多 ${result.limit||200} 条）。仅显示已同步且关联本机任务的记录。对照指标为 — 表示该次未运行或未保存对照。`:'实验同步尚未启用。启用后可在这里研究已同步结果。');
      }catch(error){message(`实验加载失败：${error.message}。可点击刷新重试。`);}finally{loading=false;nodes.refresh.disabled=false;for(const resolve of loadWaiters.splice(0))resolve();}
    }
    nodes.refresh.onclick=load;nodes.filter.oninput=render;nodes.strategy.onchange=render;
    return {load,open:()=>{if(!loaded)return load();},render};
  }
  const exported={metric,changedParameters,comparisonWarnings,matches,toggleSelection,createResearch};
  if(typeof module!=='undefined')module.exports=exported;
  if(typeof document!=='undefined'){
    const panel=document.getElementById('panel-experiments');if(!panel)return;
    const nodes=Object.fromEntries(['status','filter','strategy','list','comparison','editor','refresh','advanced'].map(key=>[key,document.getElementById(`research-${key}`)]));
    // studies.js loads next; resolve its view when the user clicks, after initialization.
    const view=createResearch({api,el,nodes,strategyName,strategies:()=>state.strategies,showJob,copyRequest,activateTab,beginStudy:item=>root.StudiesWorkbench.openForm(item)});
    // Observe visibility so mouse, keyboard and programmatic tab switches all load lazily.
    new MutationObserver(()=>{if(!panel.hidden)view.open();}).observe(panel,{attributes:true,attributeFilter:['hidden']});
    if(!panel.hidden)view.open();
    root.ResearchExperiments=view;
  }
})(globalThis);
