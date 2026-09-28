/* 展示运行时留下的事实，不重新计算选股，也不根据成交结果猜测历史决策。 */
(function(root){
'use strict';
const number=v=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('zh-CN',{maximumFractionDigits:6});
const percent=v=>v==null?'—':`${number(Number(v)*100)}%`;
const momentum=id=>['price_momentum','qlib_momentum'].includes(id);
function ruleLines(request={}) {
 const p=request.parameters||{}, hold=request.holding_period_days??'待填写';
 const selection=momentum(request.strategy_id)?`候选 ${(p.candidate_symbols||[]).join('、')||'待选择'}：今天收盘价 ÷ ${p.lookback??'N'} 个交易日前收盘价 − 1；保留动量 ≥ ${percent(p.minimum_momentum)} 的证券，取动量最高的一只，同分按代码升序。排除历史不足、价格无效以及当日已知停牌或涨跌停的候选。`:
 request.strategy_id==='fixed_asset'?`固定买入 ${p.symbol||'待选择'}，不比较候选动量。`:'横截面排名：按当前配置的因子窗口和权重计算综合分数，选择排名最高的一只；本轮未提供逐候选评分解释。';
 return [`市场下跌触发 → ${momentum(request.strategy_id)?'N 日动量最高的一只':request.strategy_id==='fixed_asset'?'固定标的':'横截面综合排名'} → 持有 ${hold} 个交易日`,
 `收盘时下跌家数 ≥ ${number(request.min_declining_count)}，且上证指数（000001.SH）日收益 ≤ ${percent(request.trigger_return_threshold)}，空仓才进行选择。`,selection,
 `收盘生成信号，下一交易日开盘尝试买入；买入日之后经过 ${hold} 个交易日，在开盘尝试卖出（按交易日历，不是自然日）。`,
 '未知交易状态按可成交假设处理；数据中的 False 不代表已验证可交易。',
 '单持仓，按可用资金和交易单位尽量买入；持仓时不加仓、不换仓。没有止盈止损，不因动量排名变化提前卖出。买入受阻取消，卖出受阻顺延。',
 request.strategy_id==='qlib_momentum'?'计算引擎：Qlib，仅计算动量因子；没有模型训练、AI 预测，交易由本系统执行。':momentum(request.strategy_id)?'计算引擎：本地价格规则；相对更强不表示正在上涨，也不预测未来收益。':'费用、滑点及已知交易限制沿用本次回测配置。'];
}
function reasonText(reason) {return ({insufficient_history:'历史长度不足',duplicate_dates:'日期重复',missing_current_bar:'缺少当日行情',invalid_price:'价格无效',is_suspended:'已知停牌',limit_up:'已知涨停',limit_down:'已知跌停',below_minimum:'低于最低动量门槛',lower_score:'动量低于获选证券',tie_break:'同分，按证券代码升序落后',selected:'动量最高且通过筛选',missing_factor:'缺少 Qlib 因子分数','insufficient cash':'资金不足',insufficient_cash:'资金不足',missing_row:'缺少当日行情',invalid_open:'开盘价无效',suspended:'已知停牌'})[reason]||reason||'—';}
function decisionSummary(e) {return ({market_data_unavailable:'市场数据不可用，无法判断触发条件；未计算候选分数。',market_not_triggered:'市场条件未满足；未计算候选分数。',holding:`已有持仓 ${e.position_symbol||'—'}，不重新择股；未计算候选分数。`,selected:`选中 ${e.selected_symbol||'—'}，计划 ${e.planned_entry_date||'未确定'} 开盘买入。`,no_candidate:'市场触发，但没有候选通过筛选。',no_next_session:'样本内无下一交易日，无法安排买入。'})[e.status]||`决策状态：${e.status||'未知'}`;}
function executionRow(e) {return [e.signal_date||'未记录',e.planned_entry_date||'—',e.date,e.symbol,e.side==='buy'?'买入':'卖出',({filled:'成交',cancelled:'取消',deferred:'延后'})[e.status]||e.status,e.entry_date||'未成交 / 未记录',e.planned_exit_date||'未确定（样本内无日期或未成交）',reasonText(e.reason)];}
function node(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;}
function renderRule(target,request,label='本次策略规则') {target.replaceChildren();const lines=ruleLines(request);target.append(node('h3',label),node('p',lines[0],'rule-title'));const list=node('ul');lines.slice(1).forEach(line=>list.append(node('li',line)));target.append(list);}
function grid(headers,rows){const wrap=node('div',null,'table-wrap');const t=node('table'),head=node('thead'),hr=node('tr'),body=node('tbody');headers.forEach(h=>hr.append(node('th',h)));head.append(hr);rows.forEach(row=>{const tr=node('tr');row.forEach(v=>tr.append(node('td',v??'—')));body.append(tr);});t.append(head,body);wrap.append(t);return wrap;}
function renderResult(target,result,request){
 const section=node('section',null,'strategy-explanations');const rule=node('details');rule.append(node('summary','本次任务的策略规则（冻结参数）'));const card=node('div');renderRule(card,request);rule.append(card);section.append(rule);target.append(section);
 if(!Array.isArray(result.decision_events)){section.append(node('p','此历史任务尚未记录逐日决策解释。请复制参数重跑以生成解释；原结果保持不变。','hint'));return;}
 const details=node('details');details.open=true;details.append(node('summary','为什么选它 · 逐日决策'));
 const dates=result.decision_events,controls=node('div',null,'actions'),label=node('label','决策日期 '),select=node('select');select.setAttribute('aria-label','决策日期');dates.forEach((e,i)=>{const option=node('option',`${e.date} · ${e.selected_symbol||({market_data_unavailable:'市场数据不可用',holding:'持仓中',market_not_triggered:'未触发',no_candidate:'无候选',no_next_session:'无下一交易日'})[e.status]||e.status}`);option.value=String(i);select.append(option);});label.append(select);
 const previous=node('button','上一日'),next=node('button','下一日');previous.type=next.type='button';controls.append(previous,label,next);const content=node('div');details.append(controls,content);section.append(details);
 // 只渲染当前日期的候选，避免多年数据一次生成大量 DOM。
 function show(){const i=Number(select.value),e=dates[i];content.replaceChildren();previous.disabled=i<=0;next.disabled=i>=dates.length-1;if(!e){content.append(node('p','本次没有可展示的决策日期。'));return;}
 content.append(node('p',`下跌家数 ${number(e.declining_count)} · 指数日收益 ${percent(e.index_return_1d)} · 市场触发：${e.status==='market_data_unavailable'?'无法判断':e.market_triggered?'是':'否'}`),node('p',decisionSummary(e),'rule-title'));
 if(e.market_warning)content.append(node('p',e.market_warning,'warnings'));
 const evaluated=!['holding','market_not_triggered','market_data_unavailable'].includes(e.status);
 if(evaluated&&e.candidate_details_supported===false)content.append(node('p','此策略运行不支持逐候选分数解释；仍可查看市场触发和执行时间线。','hint'));
 else if(evaluated&&!momentum(request.strategy_id))content.append(node('p','本轮逐候选分数解释仅支持本地动量和 Qlib 动量；此策略仍可查看市场触发和执行时间线。','hint'));
 else if(evaluated&&e.candidates?.length)content.append(grid(['证券','动量','参考日期','参考收盘价','当日收盘价','状态 / 原因'],e.candidates.map(c=>[c.symbol,percent(c.score),c.reference_date||'—',number(c.reference_close),number(c.current_close),`${({selected:'获选',eligible:'合格',excluded:'排除'})[c.status]||c.status} · ${reasonText(c.reason)}`])));
 }
 select.onchange=show;previous.onclick=()=>{select.value=String(Number(select.value)-1);show();};next.onclick=()=>{select.value=String(Number(select.value)+1);show();};const first=dates.findIndex(e=>e.status==='selected');if(first>=0)select.value=String(first);show();
 if(request.strategy_id==='qlib_momentum')details.append(node('p','Qlib 分数采用因子引擎实际输出；因内部数值精度，可能与表中价格手算结果存在微小差异。','hint'));
 const timeline=node('details');timeline.append(node('summary','交易时间线 · 信号、计划与实际执行'),node('p','信号日为历史收盘决策日；计划买入在其下一交易日，不是当前实时下单建议。计划卖出日来自实际买入日 + 持有交易日数。未知表示未成交或样本日历不足，不推算未来日期。','hint'));
 const events=result.execution_events||[],pageSize=20;let page=0;const paging=node('div',null,'actions'),back=node('button','上一页'),forward=node('button','下一页'),counter=node('span'),rows=node('div');back.type=forward.type='button';paging.append(back,counter,forward);timeline.append(paging,rows);section.append(timeline);
 function showPage(){rows.replaceChildren();counter.textContent=`${page+1} / ${Math.max(1,Math.ceil(events.length/pageSize))} 页 · ${events.length} 条执行记录`;back.disabled=page===0;forward.disabled=(page+1)*pageSize>=events.length;rows.append(events.length?grid(['信号日','计划买入日','执行日','证券','方向','结果','实际买入日','计划卖出日','原因'],events.slice(page*pageSize,(page+1)*pageSize).map(executionRow)):node('p','没有执行事件；请结合逐日决策查看原因。'));}back.onclick=()=>{page--;showPage();};forward.onclick=()=>{page++;showPage();};showPage();
}
const api={ruleLines,reasonText,decisionSummary,executionRow,renderRule,renderResult};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.StrategyExplanations=api;
})(globalThis);
