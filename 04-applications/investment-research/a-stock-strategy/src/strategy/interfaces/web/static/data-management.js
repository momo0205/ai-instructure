/* 独立行情资产与可回测输入是不同状态；本模块只展示服务端已经验证的覆盖。 */
(function(root){
'use strict';
function groupAssets(assets,query='') {
 const groups=new Map(),needle=query.trim().toLowerCase();
 for(const asset of assets||[]){if(needle&&!`${asset.symbol} ${asset.name}`.toLowerCase().includes(needle))continue;if(!groups.has(asset.symbol))groups.set(asset.symbol,{symbol:asset.symbol,name:asset.name,versions:[]});groups.get(asset.symbol).versions.push(asset);}
 return [...groups.values()];
}
function readinessText(r={}){return r.status==='ready'?`可准备研究输入：${r.start} — ${r.end}`:r.status==='partial'?`部分区间可研究：${r.start} — ${r.end}`:'当前策略暂不可运行';}
// 前复权基准随更新变化，必须重取完整请求区间，不能把新日期拼到旧版本尾部。
function updateRequest(asset,today){return {symbol:asset.symbol,start:asset.requested_start||asset.start,end:today};}
function create({api,selectDataset,refresh}) {
 const $=id=>document.getElementById(id);let data={assets:[],foundations:[],legacy_versions:[]},detailGeneration=0,selected=null;
 const n=(tag,text,cls)=>{const e=document.createElement(tag);if(text!=null)e.textContent=text;if(cls)e.className=cls;return e;};
 const button=(text,action)=>{const b=n('button',text);b.type='button';b.onclick=action;return b;};
 function select(tab){document.querySelectorAll('[data-data-tab]').forEach(b=>{const active=b.dataset.dataTab===tab;b.setAttribute('aria-selected',String(active));b.classList.toggle('active',active);});document.querySelectorAll('[data-data-panel]').forEach(p=>p.hidden=p.dataset.dataPanel!==tab);}
 function message(error){$('download-notice').textContent=error.message||String(error);}
 function grid(headers,rows){const wrap=n('div',null,'scroll'),t=n('table'),h=n('tr');headers.forEach(s=>h.append(n('th',s)));const head=n('thead');head.append(h);t.append(head);const body=n('tbody');rows.forEach(row=>{const tr=n('tr');row.forEach(v=>tr.append(n('td',v??'—')));body.append(tr);});t.append(body);wrap.append(t);return wrap;}
 function fill(request){select('assets');for(const key of ['symbol','start','end'])$(`download-${key}`).value=request[key]||'';$('download-form').scrollIntoView({behavior:'smooth',block:'center'});$('download-symbol').focus();}
 function legacyRows(){return data.legacy_versions||[];}
 function renderAssets(){const box=$('data-assets');box.replaceChildren();const groups=groupAssets(data.assets,$('asset-search').value);
  for(const group of groups){const card=n('section',null,'data-security');card.append(n('h3',`${group.name||group.symbol} · ${group.symbol}`));for(const asset of group.versions){const row=n('div',null,'data-version');const text=n('div');text.append(n('strong',`${asset.start||'—'} — ${asset.end||'—'}`),n('p',`${asset.source||'来源未声明'} · ${asset.adjustment||'复权未声明'} · ${asset.rows??'—'} 条 · ${asset.id}`,'hint'),n('p',readinessText(asset.readiness),'hint'));row.append(text,button('查看行情详情',()=>openAsset(asset.id).catch(message)));card.append(row);}box.append(card);}
  if(!groups.length)box.append(n('p','暂无符合条件的独立行情资产。可下载新行情；已有研究版本仍在下方保留。','hint'));
  const q=$('asset-search').value.trim().toLowerCase(),rows=[];
  for(const version of legacyRows())for(const i of version.instruments||[]){if(q&&!`${i.symbol} ${i.name}`.toLowerCase().includes(q))continue;rows.push([version.name||version.id,`${i.name||''} · ${i.symbol}`,`${i.start||version.start} — ${i.end||version.end}`,i.backtest_supported?'已保存研究版本':'仅行情 / 以策略检查为准']);}
  $('instruments').replaceChildren(rows.length?grid(['历史研究版本','证券','覆盖区间','用途'],rows):n('p','暂无匹配的历史研究版本。','hint'));
 }
 async function openAsset(id){const generation=++detailGeneration;selected=id;select('assets');$('asset-detail').hidden=false;$('asset-detail').replaceChildren(n('p','正在读取行情详情…','hint'));const asset=await api(`/api/data-assets/${encodeURIComponent(id)}`);if(generation!==detailGeneration)return;renderDetail(asset);}
 function renderDetail(asset){const box=$('asset-detail');box.replaceChildren();box.append(n('h3',`${asset.name||asset.symbol} · 行情详情`));box.append(grid(['项目','内容'],[['证券',asset.symbol],['版本',asset.id],['请求区间',`${asset.requested_start} — ${asset.requested_end}`],['实际覆盖',`${asset.start} — ${asset.end}`],['行数',asset.rows],['来源 / 复权',`${asset.source||'—'} / ${({qfq:'前复权',none:'不复权'})[asset.adjustment]||asset.adjustment||'—'}`],['生成时间',asset.created_at],['覆盖检查',({matches_observed_index:'与本次观测指数日期一致（非完整日历认证）',gaps_detected:'存在缺失日期，原因待核实',calendar_unverified:'没有指数参照，完整性未验证'})[asset.quality?.coverage_status]||'未验证']]));
  box.append(n('p',readinessText(asset.readiness),'data-readiness'));for(const reason of asset.readiness?.reasons||[])box.append(n('p',reason,'hint'));for(const warning of asset.warnings||[])box.append(n('p',warning,'hint'));
  if(asset.quality?.missing_dates?.length)box.append(n('p',`缺失日期：${asset.quality.missing_dates.join('、')}`,'warnings'));
  const actions=n('div',null,'actions');actions.append(button('更新至今日（重新下载完整区间）',()=>fill(updateRequest(asset,data.today))),button('下载自定义区间',()=>fill({symbol:asset.symbol,start:asset.requested_start||asset.start,end:asset.requested_end||asset.end})));
  const use=button('准备可用区间并带入回测',async()=>{use.disabled=true;try{const result=await api(`/api/data-assets/${encodeURIComponent(asset.id)}/research`,{});await refresh();selectDataset(result.dataset_id,{symbol:asset.symbol,start:result.start,end:result.end});$('download-notice').textContent=`已准备 ${result.start} — ${result.end} 的研究输入；原始行情资产保留。`;}catch(e){message(e);}finally{use.disabled=false;}});use.disabled=!['ready','partial'].includes(asset.readiness?.status);actions.append(use);box.append(actions,n('p','更新会生成新版本，前复权行情不追加拼接；旧回测和旧版本保留。请求结束日不保证当日收盘数据已经发布。','hint'));
  const rows=asset.preview||[];box.append(n('h3','行情预览（最多 100 条）'),grid(['日期','开盘','最高','最低','收盘','成交量'],rows.map(r=>[r.date,r.open,r.high,r.low,r.close,r.volume])));box.scrollIntoView({behavior:'smooth',block:'start'});
 }
 function renderOverview(downloads){const groups=groupAssets(data.assets),box=$('data-overview');box.replaceChildren();const cards=n('div',null,'metrics');for(const [label,value] of [['独立行情证券',groups.length],['行情版本',(data.assets||[]).length],['待执行下载',downloads.filter(j=>['queued','running'].includes(j.status)).length],['依赖待补齐',(data.assets||[]).filter(a=>a.readiness?.status!=='ready').length]]){const c=n('div',null,'metric');c.append(n('small',label),n('strong',String(value)));cards.append(c);}box.append(cards,n('p',`服务端日期：${data.today||'—'}（中国时区）。行情、指数和市场广度分别管理；下载成功不等于策略依赖齐全。`,'hint'));
  for(const f of data.foundations||[])box.append(n('p',`市场基础 ${f.name||f.id}：指数 ${f.index_start||'—'} — ${f.index_end||'—'}；广度 ${f.breadth_start||'—'} — ${f.breadth_end||'—'}`,'data-readiness'));
  if(!(data.foundations||[]).length)box.append(n('p','尚无市场基础数据。仍可下载行情；当前市场触发策略需补齐指数与广度后才能运行。','warnings'));
  for(const error of data.errors||[])box.append(n('p',typeof error==='string'?error:JSON.stringify(error),'warnings'));box.append(button('新增证券 / 下载行情',()=>select('assets')));
 }
 function renderFoundations(){const box=$('data-foundations');box.replaceChildren();for(const f of data.foundations||[]){const card=n('section',null,'data-security');card.append(n('h3',f.name||f.id),grid(['数据依赖','起始日期','末尾日期'],[['指数行情',f.index_start,f.index_end],['市场广度',f.breadth_start,f.breadth_end]]));for(const warning of [...(f.warnings||[]),...(f.errors||[]),...(f.calendar_status?[f.calendar_status]:[])])card.append(n('p',warning,'hint'));box.append(card);}box.append(n('p','本阶段展示现有基础数据覆盖；交易日历是否完整不能仅由行情日期判断。指数和广度更新能力将分别建设，当前不会自动生成或填补缺失广度。','hint'));}
 function renderDownloads(downloads){const box=$('downloads');box.replaceChildren();if(!downloads.length)box.append(n('p','暂无下载任务。','hint'));for(const job of downloads){const row=n('div',null,'download-row');row.append(n('strong',`${job.request?.symbol||''} · ${job.request?.start||''} — ${job.request?.end||''}`),n('span',({queued:'排队中',running:'下载中',succeeded:'行情下载完成',failed:'失败',interrupted:'已中断'})[job.status]||job.status,'status'));if(job.progress)row.append(n('p',job.progress.message||({resolving:'识别证券',downloading:'获取行情',validating:'校验行情'})[job.progress.stage]||'处理中','hint'));row.append(n('p',`任务编号：${job.id}`,'hint'));if(job.error)row.append(n('p',`${job.error}${job.diagnostic?.code?' ['+job.diagnostic.code+']':''}`,'warnings'));
  if(job.status==='succeeded'&&job.dataset_id)row.append(button(job.dataset_id.startsWith('asset_')?'查看行情与依赖':'查看此数据集',()=>job.dataset_id.startsWith('asset_')?openAsset(job.dataset_id).catch(message):selectDataset(job.dataset_id)));
  if(['failed','interrupted'].includes(job.status))row.append(button('重试下载',async event=>{const retry=event.currentTarget;retry.disabled=true;try{await api('/api/downloads',job.request);await refresh();}catch(e){message(e);}finally{retry.disabled=false;}}));box.append(row);}}
 function render(value,downloads=[]){data=value;const today=data.today;if(today)for(const key of ['start','end']){const input=$(`download-${key}`);input.removeAttribute('min');input.max=today;if(!input.value)input.value=key==='start'?`${today.slice(0,4)}-01-01`:today;}$('download-coverage').textContent='下载日期独立于旧回测基线；实际可取得范围取决于上市时间、供应商覆盖及数据发布时间。当前来源：腾讯。';renderAssets();renderOverview(downloads);renderFoundations();renderDownloads(downloads);}
 document.querySelectorAll('[data-data-tab]').forEach(b=>b.onclick=()=>select(b.dataset.dataTab));$('asset-search').oninput=renderAssets;
 return {render,openAsset,select};
}
const exports={groupAssets,readinessText,updateRequest,create};if(typeof module!=='undefined')module.exports=exports;root.DataManagement=exports;
})(globalThis);
