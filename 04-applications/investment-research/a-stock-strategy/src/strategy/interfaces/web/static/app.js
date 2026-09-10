/* 页面只负责输入与展示。策略定义和参数校验的最终依据来自服务器目录。 */
'use strict';
const $ = id => document.getElementById(id);
const state = {strategies: [], datasets: [], jobs: [], downloads: [], selected: null, compared: new Set(), busy: false};
const statuses = {queued:'排队中',running:'运行中',succeeded:'已完成',failed:'失败',cancelled:'已取消',interrupted:'已中断'};
const fmt = n => n == null || !Number.isFinite(Number(n)) ? '—' : Number(n).toLocaleString('zh-CN',{maximumFractionDigits:2});
const pct = n => n == null ? '—' : `${fmt(Number(n)*100)}%`;
function el(tag, text, cls) { const n=document.createElement(tag); if(text!=null)n.textContent=text; if(cls)n.className=cls; return n; }
function notice(text) {$('notice').textContent=text;$('notice').hidden=!text;}
async function api(path, body) {
  const response=await fetch(path, body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const result=await response.json(); if(!response.ok)throw new Error(result.error||'请求失败'); return result;
}
function strategyName(id) {return state.strategies.find(s=>s.id===id)?.name||id;}
function strategyFields(values={}) {
  const spec=state.strategies.find(s=>s.id===$('strategy').value); const container=$('strategy-parameters');container.replaceChildren();
  if(!spec)return; $('strategy-description').textContent=spec.description;
  for(const field of spec.parameters) {
    const label=el('label',field.label||field.name); const value=values[field.name]??field.default;
    let input;
    if(field.role==='instrument') {
      input=el('select');input.multiple=field.type==='array';
      const selected=Array.isArray(value)?value:[value];
      const items=InstrumentChoices.available(state.datasets.find(d=>d.id===$('dataset').value));
      if(!input.multiple) input.append(new Option('请选择已准备的标的',''));
      for(const item of items) {
        const option=new Option(`${item.name} · ${item.symbol}`,item.symbol);
        option.selected=selected.includes(item.symbol);input.append(option);
      }
      if(input.multiple) {input.size=Math.min(6,Math.max(3,items.length));}
      input.onchange=()=>updateCoverage();
      if(input.multiple) label.append(el('small','可多选，按住 Ctrl / Command 选择多个标的','hint'));
    }
    else if(field.type==='boolean') {input=el('input');input.type='checkbox';input.checked=value;}
    else if(['object','array'].includes(field.type)) {input=el('textarea');input.value=JSON.stringify(value,null,2);}
    else if(field.options||field.enum) {input=el('select');for(const option of (field.options||field.enum)) input.append(new Option(option,option));input.value=value;}
    else {input=el('input');input.type=['integer','number','float','int'].includes(field.type)?'number':'text';
      input.value=Array.isArray(value)?value.join(', '):value??'';
      if(field.min!=null)input.min=field.min;if(field.max!=null)input.max=field.max;
      input.step=field.step??(['integer','int'].includes(field.type)?1:'any');}
    input.dataset.parameter=field.name;input.dataset.type=field.type;input.dataset.role=field.role||'';input.required=field.type!=='boolean';label.append(input);container.append(label);
    if(field.description)container.append(el('p',field.description,'hint'));
  }
  updateCoverage();
}
function selectedSymbols() {
  // Instrument intent is declared by the strategy, independent of parameter names.
  return [...new Set([...$('strategy-parameters').querySelectorAll('[data-parameter]')]
    .filter(input=>input.dataset.role==='instrument')
    .flatMap(input=>input.multiple?[...input.selectedOptions].map(o=>o.value):[input.value].filter(Boolean)))];
}
function updateCoverage() {
  const d=state.datasets.find(x=>x.id===$('dataset').value);
  const spec=state.strategies.find(s=>s.id===$('strategy').value);
  if(!spec?.parameters.some(p=>p.role==='instrument' && ['string','array'].includes(p.type))) {
    $('submit').disabled=true;$('coverage-info').textContent='该策略尚未配置页面标的选择，请通过接口执行或完善策略定义。';return null;
  }
  const range=InstrumentChoices.coverage(d,selectedSymbols());
  $('submit').disabled=!range;
  $('coverage-info').textContent=range?`所选标的共同可用区间：${range.start} — ${range.end}；区间内缺失数据会在提交时校验。`:'请选择有共同数据区间的可回测标的。';
  if(range) for(const key of ['start','end']) {
    $(key).min=range.start;$(key).max=range.end;
    if(!$(key).value || $(key).value<range.start || $(key).value>range.end) $(key).value=range[key];
  }
  return range;
}
function datasetFields(reset=true) {
  const d=state.datasets.find(x=>x.id===$('dataset').value);if(!d)return;
  $('dataset-info').textContent=`${d.sample?'样例数据 · 不代表真实市场':'真实历史数据'} · ${d.start} — ${d.end} · ${d.adjustment||'未声明复权'}\n行情：${d.market_source||'未知'}；广度：${(d.source||[]).join('、')||'未知'}\n${(d.symbols||[]).join(' / ')} ${(d.warnings||[]).join('；')}`;
  for(const key of ['start','end']) {$(key).min=d.start;$(key).max=d.end;if(reset)$(key).value=d[key];}
}
function requestFromForm() {
  if(!updateCoverage()) throw new Error('请先选择可回测标的');
  const parameters={};for(const input of $('strategy-parameters').querySelectorAll('[data-parameter]')) {
    const type=input.dataset.type;let value=input.value;
    if(['integer','number','float','int'].includes(type))value=Number(value);
    else if(input.multiple)value=[...input.selectedOptions].map(option=>option.value);
    else if(type==='boolean')value=input.checked;
    else if(type==='object'||type==='array') {
      try {value=JSON.parse(value);}catch {throw new Error(`${input.dataset.parameter} 必须填写合法 JSON ${type==='array'?'数组':'对象'}`);}
      if(type==='array'?!Array.isArray(value):value===null||Array.isArray(value)||typeof value!=='object')throw new Error(`${input.dataset.parameter} 类型应为 ${type}`);
    }
    parameters[input.dataset.parameter]=value;
  }
  const request={strategy_id:$('strategy').value,parameters,dataset_id:$('dataset').value,start:$('start').value,end:$('end').value};
  for(const key of ['initial_cash','holding_period_days','min_declining_count','trigger_return_threshold','commission_rate','minimum_commission','slippage_bps'])request[key]=Number($(key).value);
  // 页面用百分数，后端用小数；只在边界转换一次，避免 1% 与 0.01% 混淆。
  request.trigger_return_threshold/=100;request.commission_rate/=100;return request;
}
function copyRequest(request) {
  if(!state.datasets.some(d=>d.id===request.dataset_id)) {notice('原任务数据集已不可用，无法复制参数。');return;}
  $('strategy').value=request.strategy_id;$('dataset').value=request.dataset_id;datasetFields(false);strategyFields(request.parameters);
  for(const key of ['start','end','initial_cash','holding_period_days','min_declining_count','minimum_commission','slippage_bps'])if(request[key]!=null)$(key).value=request[key];
  for(const key of ['trigger_return_threshold','commission_rate'])if(request[key]!=null)$(key).value=Number(request[key])*100;
  notice('已复制参数。调整后点击“开始回测”会创建一个新任务。');$('run-form').scrollIntoView({behavior:'smooth'});
}
function renderJobs() {
  const box=$('jobs');box.replaceChildren();if(!state.jobs.length){box.append(el('p','还没有任务。从左侧开始第一次回测。','muted'));return;}
  for(const job of state.jobs) {
    const row=el('div',null,'job');const check=el('input');check.type='checkbox';check.checked=state.compared.has(job.id);check.disabled=job.status!=='succeeded';check.setAttribute('aria-label',`对比 ${job.id}`);
    check.onchange=()=>{check.checked?state.compared.add(job.id):state.compared.delete(job.id);renderComparison().catch(e=>notice(e.message));};row.append(check);
    const button=el('button');button.type='button';button.append(el('span',strategyName(job.request?.strategy_id),'job-title'));
    button.append(el('span',`${job.request?.start||''} → ${job.request?.end||''} · ${job.id.slice(0,8)}`,'job-meta'));
    button.onclick=()=>showJob(job.id).catch(e=>notice(e.message));row.append(button,el('span',statuses[job.status]||job.status,`status ${job.status}`));box.append(row);
  }
}
function table(headers, rows) {
  const wrap=el('div',null,'scroll'),t=el('table'),head=el('thead'),tr=el('tr');headers.forEach(h=>tr.append(el('th',h)));head.append(tr);t.append(head);
  const body=el('tbody');for(const row of rows){const r=el('tr');row.forEach(v=>r.append(el('td',v??'—')));body.append(r);}t.append(body);wrap.append(t);return wrap;
}
function chart(points, key, title, percent=false) {
  const section=el('div');section.append(el('div',title,'chart-title'));if(!points.length){section.append(el('p','暂无曲线数据','hint'));return section;}
  const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 760 205');svg.classList.add('chart');svg.setAttribute('role','img');svg.setAttribute('aria-label',title);
  const values=points.map(p=>Number(p[key]));let low=Math.min(...values),high=Math.max(...values);if(low===high){low-=1;high+=1;}
  const x=i=>70+i/Math.max(1,points.length-1)*670,y=v=>165-(v-low)/(high-low)*145;
  function node(tag,attrs,text){const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text)n.textContent=text;svg.append(n);return n;}
  for(let i=0;i<4;i++){const v=low+(high-low)*i/3;node('line',{x1:70,x2:740,y1:y(v),y2:y(v)});node('text',{x:62,y:y(v)+4,'text-anchor':'end'},percent?pct(v):fmt(v));}
  node('polyline',{points:values.map((v,i)=>`${x(i)},${y(v)}`).join(' '),fill:'none',stroke:percent?'#b78657':'#16776b','stroke-width':2.2});
  node('text',{x:70,y:193},String(points[0].date));node('text',{x:740,y:193,'text-anchor':'end'},String(points.at(-1).date));section.append(svg);return section;
}
function download(result, id) {
  const a=el('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));a.download=`backtest-${id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
}
// 从执行日志解释空结果；已买入但未卖出的任务不能误报为从未成交。
function noTradeMessage(result) {
  if(result.trades?.length)return '';
  const entries=(result.execution_events||[]).filter(e=>e.side==='buy');
  if(entries.some(e=>e.status==='filled'))return '本次已买入，但尚未完成卖出。胜率暂无样本；请查看期末持仓与卖出延后记录。';
  const insufficient=entries.filter(e=>e.status==='cancelled'&&e.reason==='insufficient_cash').length;
  if(insufficient)return `本次没有买入成交：${insufficient} 次买入因资金不足取消。请检查初始资金是否足够支付最小买入数量及费用；股票按 100 股整手买入。可复制参数、调整模拟初始资金后重跑。当前收益与回撤仅表示账户未发生交易，不能据此评价策略。`;
  return '本次没有完成交易，胜率暂无样本。请检查触发条件、数据预热和成交取消记录；旧任务还需检查期末未平仓说明。';
}
async function showJob(id) {
  state.selected=id;const job=await api(`/api/jobs/${id}`);if(state.selected!==id)return;
  const box=$('detail');box.replaceChildren();const title=el('div',null,'section-title');title.append(el('h2',strategyName(job.request?.strategy_id)),el('span',statuses[job.status]||job.status,`status ${job.status}`));box.append(title);
  const actions=el('div',null,'actions');const copy=el('button','复制参数重跑');copy.onclick=()=>copyRequest(job.request);actions.append(copy);
  if(['queued','running'].includes(job.status)){const cancel=el('button','取消任务');cancel.onclick=async()=>{try{await api(`/api/jobs/${id}/cancel`,{});await refresh();await showJob(id);}catch(e){notice(e.message);}};actions.append(cancel);}
  box.append(actions);
  if(job.status!=='succeeded') {box.append(el('p',job.error||(['running','queued'].includes(job.status)?'后台处理中，可关闭页面后再回来查看。':'此任务未产生回测结果。'),'hint'));return;}
  const r=job.result;if(!r){box.append(el('p','结果文件不可用','warnings'));return;}
  const exportButton=el('button','导出结果 JSON');exportButton.onclick=()=>download(r,id);actions.append(exportButton);
  const emptyMessage=noTradeMessage(r);if(emptyMessage)box.append(el('p',emptyMessage,'warnings'));
  const metrics=el('div',null,'metrics');for(const [label,key,isPct] of [['累计收益','cumulative_return',true],['最大回撤','max_drawdown',true],['胜率','win_rate',true],['交易次数','trade_count',false]]){
    const card=el('div',null,'metric');card.append(el('small',label),el('strong',key==='win_rate'&&!r.trades?.length?'—':isPct?pct(r.metrics[key]):fmt(r.metrics[key]),Number(r.metrics[key])<0?'negative':''));metrics.append(card);}box.append(metrics);
  if(r.warnings?.length){const warnings=el('ul',null,'warnings');r.warnings.forEach(w=>warnings.append(el('li',w)));box.append(warnings);}
  box.append(chart(r.equity||[],'equity','账户净值（元）'),chart(r.equity||[],'drawdown','回撤',true));
  box.append(el('h2','逐笔交易','subheading'),el('p','成交日期与费用均按本次执行参数计算。','hint'));
  box.append(table(['信号日','买入日','卖出日','标的','数量','买入价','卖出价','总费用','佣金','印花税','过户费','盈亏'],(r.trades||[]).map(t=>[t.signal_date,t.entry_date,t.exit_date,t.symbol,fmt(t.quantity),fmt(t.entry_price),fmt(t.exit_price),fmt(t.fees),t.commission==null?"—":fmt(t.commission),t.stamp_duty==null?"—":fmt(t.stamp_duty),t.transfer_fee==null?"—":fmt(t.transfer_fee),fmt(t.pnl)])));
  // 旧任务没有执行日志，仍可查看原有结果。
  if(r.execution_events){const execution=el('details');execution.append(el('summary','成交、取消与延后记录'));execution.append(table(['日期','标的','方向','状态','原因','价格','数量','佣金','印花税','过户费'],r.execution_events.map(e=>[e.date,e.symbol,e.side==='buy'?'买入':'卖出',({filled:'成交',cancelled:'取消',deferred:'延后'})[e.status]||e.status,e.reason||'—',e.price==null?'—':fmt(e.price),fmt(e.quantity),fmt(e.commission),fmt(e.stamp_duty),fmt(e.transfer_fee)])));box.append(execution);}
  const events=el('details');events.append(el('summary','每日触发记录'));events.append(table(['日期','下跌家数','指数日收益','触发'],(r.events||[]).map(e=>[e.as_of,e.declining_count,pct(e.index_return_1d),e.triggered?'是':'否'])));box.append(events);
  const audit=el('details');audit.append(el('summary','参数、版本与数据依据'),el('pre',JSON.stringify({request:job.request,metadata:r.metadata},null,2)));box.append(audit);
}
async function renderComparison() {
  const target=$('comparison');target.hidden=state.compared.size===0;if(target.hidden)return;
  const jobs=await Promise.all([...state.compared].map(id=>api(`/api/jobs/${id}`)));target.replaceChildren(el('h3','已选任务对比','compare-title'),el('p','不同区间、数据版本或预热情况会影响可比性，请结合各任务说明阅读。','hint'));
  target.append(table(['策略 / 任务','区间','累计收益','年化收益','回撤','胜率','笔数'],jobs.filter(j=>j.result).map(j=>{const m=j.result.metrics;return [`${strategyName(j.request.strategy_id)} / ${j.id.slice(0,8)}`,`${j.request.start} ~ ${j.request.end}`,pct(m.cumulative_return),pct(m.annualized_return),pct(m.max_drawdown),pct(m.win_rate),m.trade_count];})));
}
async function refresh() {state.jobs=await api('/api/jobs');renderJobs();}
function renderDownloads() {
  const target=$('downloads');target.replaceChildren();
  if(!state.downloads.length) target.append(el('p','尚无下载记录。','hint'));
  for(const job of state.downloads) {
    const row=el('div',null,'download-row');
    row.append(el('strong',`${job.request.symbol} · ${statuses[job.status]||job.status}`),el('p',`${job.request.start} — ${job.request.end}`,'hint'));
    if(job.error) row.append(el('p',job.error,'warnings'));
    if(job.dataset_id) {
      const use=el('button','查看此数据集');use.type='button';
      use.onclick=()=>{$('dataset').value=job.dataset_id;datasetFields();strategyFields();$('run-form').scrollIntoView({behavior:'smooth'});};row.append(use);
    }
    if(['failed','interrupted'].includes(job.status)) {
      const retry=el('button','重试下载');retry.type='button';retry.onclick=async()=>{
        retry.disabled=true;try{await api('/api/downloads',job.request);await refreshData();}catch(e){$('download-notice').textContent=e.message;}finally{retry.disabled=false;}
      };row.append(retry);
    }
    target.append(row);
  }
}
async function refreshData() {
  // 完成状态写入晚于数据发布；先读状态再读目录，确保成功任务的版本已可见。
  const downloads=await api('/api/downloads');
  const datasets=await api('/api/datasets');
  // 等待网络期间用户可能已经切换数据集，保留响应到达时的实际选择。
  const previous=$('dataset').value;
  state.datasets=datasets;state.downloads=downloads;
  // 后台轮询只刷新目录，不重置用户正在编辑的策略参数和日期。
  $('dataset').replaceChildren(...datasets.map(d=>new Option(d.name,d.id)));
  if(datasets.some(d=>d.id===previous)) $('dataset').value=previous;
  else {datasetFields();strategyFields();}
  const rows=datasets.flatMap(d=>(d.instruments||[]).map(i=>[
    d.name,`${i.name} · ${i.symbol}`,i.kind,`${i.start} — ${i.end}`,
    i.backtest_supported?(i.kind==='stock'?'可回测 · 近似研究':'可回测'):`仅行情：${i.reason||'交易规则尚未支持'}`,
  ]));
  $('instruments').replaceChildren(rows.length?table(['数据集','标的','类型','覆盖区间','状态'],rows):el('p','暂无已准备数据','hint'));
  const base=datasets.find(d=>d.id==='real');
  $('download-submit').disabled=!base;
  $('download-coverage').textContent=base?`当前市场广度基线：${base.start} — ${base.end}，下载区间需在此范围内。`:'请先通过 CLI 准备真实行情与市场广度，合成样例不能作为下载基线。';
  if(base) for(const key of ['start','end']) {
    const input=$(`download-${key}`);input.min=base.start;input.max=base.end;
    if(!input.value)input.value=base[key];
  }
  renderDownloads();
}
$('refresh-data').onclick=()=>refreshData().catch(e=>{$('download-notice').textContent=e.message;});
$('download-form').onsubmit=async event=>{
  event.preventDefault();$('download-submit').disabled=true;$('download-notice').textContent='';
  try {
    const request={symbol:$('download-symbol').value.trim().toUpperCase(),start:$('download-start').value,end:$('download-end').value};
    await api('/api/downloads',request);$('download-notice').textContent='下载任务已提交。完成后会生成独立数据集；请在回测区选择使用。';await refreshData();
  } catch(e) {$('download-notice').textContent=e.message;}
  finally {$('download-submit').disabled=!state.datasets.some(d=>d.id==='real');}
};
$('strategy').onchange=()=>strategyFields();$('dataset').onchange=()=>{datasetFields();strategyFields();};$('refresh').onclick=()=>refresh().catch(e=>notice(e.message));
$('run-form').onsubmit=async event=>{event.preventDefault();notice('');try{const request=requestFromForm();$('submit').disabled=true;const job=await api('/api/jobs',request);await refresh();await showJob(job.id);$('detail').scrollIntoView({behavior:'smooth',block:'start'});}catch(e){notice(e.message);}finally{updateCoverage();}};
async function init() {
  [state.strategies,state.datasets]=await Promise.all([api('/api/strategies'),api('/api/datasets')]);
  state.strategies.forEach(s=>$('strategy').append(new Option(s.name,s.id)));state.datasets.forEach(d=>$('dataset').append(new Option(d.name,d.id)));
  datasetFields();strategyFields();if(!state.datasets.length){notice('尚无可用数据集，请先按 README 下载行情和市场广度。');$('submit').disabled=true;}
  await refresh();await refreshData();
  // 串行轮询，避免长任务或慢磁盘时叠加请求。只自动更新尚未结束的详情。
  setInterval(async()=>{if(state.busy)return;state.busy=true;try{const pending=state.jobs.some(j=>j.id===state.selected&&['running','queued'].includes(j.status));await refresh();if(pending)await showJob(state.selected);if(state.downloads.some(j=>['queued','running'].includes(j.status)))await refreshData();}catch(e){notice(`连接中断：${e.message}`);}finally{state.busy=false;}},2000);
}
init().catch(e=>notice(e.message));
