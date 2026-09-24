/* 目录负责输入合同；结果只展示冻结证据，绝不在浏览器重算指标。 */
(function(root){
'use strict';
const fixed={id:'fixed_holding',name:'固定持有期',description:'买入后经过指定交易日，在开盘尝试卖出。',parameters:[],supports_effectiveness:true,supports_studies:true};
let directory=[fixed];
const policy=request=>request?.exit_policy||{id:'fixed_holding',parameters:{}};
const isFixed=request=>policy(request).id==='fixed_holding';
function label(request={}) {
 const value=policy(request);if(isFixed(request))return `固定持有 ${request.holding_period_days??'待填写'} 个交易日`;
 const spec=directory.find(s=>s.id===value.id),names={window:'均线窗口',max_holding_days:'最长持有交易日'};
 return `${spec?.name||(value.id==='close_below_sma'?'收盘低于均线':value.id)} · ${Object.entries(value.parameters||{}).map(([key,v])=>`${spec?.parameters.find(p=>p.name===key)?.label||names[key]||key} ${v}`).join(' · ')}`;
}
function createEditor({catalog,el,nodes,strategy,onchange=()=>{}}) {
 directory=Array.isArray(catalog)&&catalog.length?catalog:[fixed];const controls=new Map();
 nodes.select.replaceChildren(...directory.map(spec=>{const option=el('option',spec.name);option.value=spec.id;return option;}));nodes.select.value='fixed_holding';
 const spec=()=>directory.find(s=>s.id===nodes.select.value);
 function sync(){const current=spec();nodes.holding.disabled=current?.id!=='fixed_holding';if(nodes.holding.parentElement)nodes.holding.parentElement.hidden=nodes.holding.disabled;nodes.effectiveness.disabled=strategy()!=='fixed_asset'||!current?.supports_effectiveness;
 if(nodes.effectiveness.disabled)nodes.effectiveness.checked=false;
 nodes.hint.textContent=!current?.supports_effectiveness?'当前退出规则暂不支持随机择时有效性对照；对照需要同口径退出模型。':strategy()!=='fixed_asset'?'有效性对照目前仅支持固定标的。':'买入持有 + 100 轮随机择时，运行时间较长。历史对照不能替代样本外验证。';}
 function fields(values={}){const current=spec();controls.clear();nodes.fields.replaceChildren();nodes.description.textContent=current.description||'';
 for(const field of current.parameters){const input=el('input');input.type='number';input.step=1;input.min=field.minimum;input.max=field.maximum;input.required=true;input.value=values[field.name]??field.default;input.dataset.exitParameter=field.name;const wrapper=el('label',field.label||field.name);wrapper.append(input);nodes.fields.append(wrapper);controls.set(field.name,input);}
 sync();}
 // 原生 select 先发 input 再发 change；预览允许使用尚未创建字段的默认值。
 function read(validate=true){const current=spec();if(!current)throw Error('不支持此退出规则，请刷新规则目录。');const parameters={};for(const field of current.parameters){const input=controls.get(field.name),value=Number(input?.value??field.default);if(validate&&(!input||String(input.value).trim()==='' ||!Number.isInteger(value)||value<field.minimum||value>field.maximum))throw Error(`${field.label||field.name} 须为 ${field.minimum} 至 ${field.maximum} 的整数。`);parameters[field.name]=value;}return {id:current.id,parameters};}
 function restore(request){const value=policy(request);if(!directory.some(s=>s.id===value.id))throw Error(`当前规则目录不支持 ${value.id}，不能复制为其他退出规则。`);nodes.select.value=value.id;fields(value.parameters);}
 nodes.select.onchange=()=>{fields();onchange();};fields();return {read,restore,sync};
}
const reason=code=>({'holding period':'固定持有期到期',holding_period:'固定持有期到期',close_below_sma:'收盘低于均线',max_holding_days:'最长持有期到期',close_not_below_sma:'收盘价未低于均线',indicator_unavailable:'指标未就绪',insufficient_history:'历史长度不足',missing_close:'缺少有效收盘价',pending_exit:'等待卖出',suspended:'已知停牌'})[code]||code||'—';
// 退出信号属于卖出成交证据；按同一笔持仓匹配，不能用买入信号日期替代。
function tradeExitSignal(trade,events=[]) {
 return trade.exit_signal_date||events.find(e=>e.side==='sell'&&e.status==='filled'&&e.symbol===trade.symbol&&e.entry_date===trade.entry_date&&e.date===trade.exit_date)?.exit_signal_date||null;
}
function renderEvidence(target,result,el){
 const section=el('details');section.append(el('summary','退出依据 · 逐日收盘指标与卖出计划'));target.append(section);
 if(!Array.isArray(result.exit_decision_events)){section.append(el('p','旧任务未记录退出证据；可复制参数重跑，原结果不事后重算。','hint'));return;}
 // 暖机来自服务端冻结输入；空交易也展示覆盖，不推断或补算历史。
 if(result.metadata?.exit_policy?.version)section.append(el('p',`退出规则版本：${result.metadata.exit_policy.version}`,'hint'));
 for(const [symbol,warmup] of Object.entries(result.metadata?.exit_warmup||{}))section.append(el('p',`${symbol} · 区间前暖机 ${warmup.available_prior_sessions} / 需要 ${warmup.required_prior_sessions} 个交易日 · ${warmup.ready_at_start?'起始日可用':'暖机不足，可补充更早行情'}`,'hint'));
 const events=result.exit_decision_events;if(!events.length){section.append(el('p','本次没有持仓日退出决策。','hint'));return;}
 section.append(el('p','待卖期间不重算指标，价格与均线显示为空，可回看退出信号日的原始证据。收盘指标包含当日；指标触发后最早下一交易日开盘尝试卖出。待卖受阻顺延且不撤销；没有下一交易日时保留持仓。暖机数量来自本次冻结输入，不足时可补充更早行情。','hint'));
 const body=el('div'),nav=el('div'),previous=el('button','上一页退出证据'),next=el('button','下一页退出证据'),counter=el('span');previous.type=next.type='button';nav.className='actions';nav.append(previous,counter,next);section.append(nav,body);let page=0;const size=20;
 function show(){body.replaceChildren();previous.disabled=page===0;next.disabled=(page+1)*size>=events.length;counter.textContent=`${page+1} / ${Math.ceil(events.length/size)} 页 · ${events.length} 条`;const wrap=el('div');wrap.className='table-wrap';const table=el('table'),head=el('tr');for(const title of ['日期','证券','状态 / 原因','收盘价','SMA','暖机可用 / 窗口','已持有交易日','退出信号日','计划卖出日'])head.append(el('th',title));table.append(head);
 for(const event of events.slice(page*size,(page+1)*size)){const row=el('tr'),status=({hold:'继续持有',triggered:'触发退出',pending:'等待卖出',close_not_below_sma:'收盘价未低于均线',indicator_unavailable:'指标未就绪'})[event.status]||event.status;for(const value of [event.date,event.symbol,`${status} · ${event.status==='hold'&&event.reason==='holding_period'?'按固定持有期等待':reason(event.reason)}`,event.close==null?'—':Number(event.close).toLocaleString('zh-CN',{maximumFractionDigits:6}),event.sma==null?'—':Number(event.sma).toLocaleString('zh-CN',{maximumFractionDigits:6}),event.window==null?'—':`${event.available??'—'} / ${event.window}`,event.held_sessions,event.exit_signal_date||'—',event.planned_exit_date||'未确定（无样本内执行日）'])row.append(el('td',value??'—'));table.append(row);}wrap.append(table);body.append(wrap);}
 previous.onclick=()=>{page--;show();};next.onclick=()=>{page++;show();};show();
}
const api={createEditor,label,isFixed,policy,renderEvidence,reason,tradeExitSignal};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ExitPolicies=api;
})(globalThis);
