(function(root){
  'use strict';
  const DAY=86400000;
  const day=value=>Date.parse(String(value)+'T00:00:00Z')/DAY;
  function scaleSegment(segment,range){
    const start=day(range.start),end=day(range.end),a=Math.max(start,day(segment.start)),b=Math.min(end,day(segment.end));
    if(![start,end,a,b].every(Number.isFinite)||end<start||b<a)return null;
    return {x:(a-start)/(end-start+1)*1000,width:(b-a+1)/(end-start+1)*1000};
  }
  const versions=root.DataVersions||(typeof require==='function'?require('./data-versions.js'):null);
  const groupAssets=versions.groupAssets;
  function create({onResearch,onFill,onMarketFill}={}){
    let disclosures=[];
    const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;};
    const svgEl=(tag,attrs)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n;};
    function render(coverage={},assets=[]){
      const host=document.getElementById('coverage-timeline');if(!host)return;
      const opened=new Map(disclosures.map(([key,node])=>[key,node.open]));disclosures=[];host.replaceChildren();
      const dates=[];const collect=i=>{if(i&&Number.isFinite(day(i.start))&&Number.isFinite(day(i.end)))dates.push(i.start,i.end);};
      collect(coverage);for(const key of ['index','breadth','common'])for(const i of coverage[key]||[])collect(i);
      for(const a of assets){collect(a);for(const key of ['market','research','missing'])for(const i of a.coverage?.[key]||[])collect(i);}
      dates.sort();const range={start:dates[0],end:dates[dates.length-1]};
      host.append(el('h3','数据覆盖时间轴'),el('p','绿色表示该段数据已具备；不保证策略预热窗口或交易规则满足要求。各行情版本独立展示，不拼接前复权历史。','hint'));
      const legend=el('div',undefined,'timeline-legend');for(const [cls,label] of [['market','行情 / 基础覆盖'],['research','共同 / 可研究'],['missing','缺口'],['conflict','冲突']])legend.append(el('span',label,'timeline-key '+cls));host.append(legend);
      if(!dates.length){host.append(el('p','暂无可展示的数据覆盖，请先下载行情或更新市场基础数据。','hint'));return;}
      const axis=el('div',undefined,'timeline-axis');axis.append(el('span',range.start),el('span',range.end));host.append(axis);
      function row(parent,label,intervals,kind,action){
        const container=el('div',undefined,'timeline-row');container.append(el('strong',label));
        const chart=svgEl('svg',{viewBox:'0 0 1000 24',preserveAspectRatio:'none',role:'img','aria-label':label+'覆盖区间',class:'timeline-bar'});chart.append(svgEl('rect',{x:0,y:6,width:1000,height:12,rx:3,class:'timeline-track'}));
        const list=el('div',undefined,'timeline-intervals');
        for(const i of intervals||[]){const position=scaleSegment(i,range);if(!position)continue;const rect=svgEl('rect',{x:position.x,y:4,width:Math.max(position.width,1),height:16,rx:2,class:'timeline-segment '+kind});const title=svgEl('title',{});title.textContent=label+' '+i.start+' 至 '+i.end;rect.append(title);chart.append(rect);
          const description=i.start+' 至 '+i.end+(i.days?' · '+i.days+(kind==='missing'?' 个待核验工作日':' 个交易日'):'')+(i.reason?' · '+i.reason:'');
          if(action){const button=el('button',action.label+' '+description);button.type='button';button.onclick=()=>action.run(i);list.append(button);}else list.append(el('span',description));
        }
        container.append(chart,list);if(!(intervals||[]).length)list.append(el('span','暂无覆盖','hint'));parent.append(container);
      }
      row(host,'指数基础',coverage.index,'market');row(host,'市场广度',coverage.breadth,'market');row(host,'基础共同覆盖',coverage.common,'research');
      const conflicts=(coverage.conflicts||[]).map(c=>({start:c.date,end:c.date,reason:(c.kind||'')+' '+(c.sources||[]).join(' / ')}));if(conflicts.length)row(host,'基础数据冲突',conflicts,'conflict');
      if(coverage.calendar_status&&coverage.calendar_status!=='ready')host.append(el('p','休市日期根据已保留的数据源空响应判断，尚未通过独立交易日历验证。','hint'));
      for(const error of coverage.errors||[])host.append(el('p',typeof error==='string'?error:JSON.stringify(error),'hint'));
      function disclosure(parent,key,label){const d=el('details',undefined,'timeline-disclosure');d.open=opened.get(key)||false;d.append(el('summary',label));disclosures.push([key,d]);parent.append(d);return d;}
      function assetRows(parent,asset){const c=asset.coverage||{};
        row(parent,'行情覆盖',c.market?.length?c.market:(asset.start&&asset.end?[{start:asset.start,end:asset.end}]:[]),'market');
        row(parent,'可研究区间',versions.research(asset),'research',onResearch?{label:'研究此区间',run:i=>onResearch(asset.id,i.start,i.end)}:null);
        const missing=(c.missing||[]).filter(i=>i.reason!=='缺少证券行情');if(missing.length)row(parent,'缺失基础数据',missing,'missing',onFill?{label:'补齐基础数据',run:i=>onFill(i.start,i.end)}:null);
        const quoteGaps=(c.missing||[]).filter(i=>i.reason==='缺少证券行情');if(quoteGaps.length)row(parent,'行情缺口',quoteGaps,'missing',onMarketFill?{label:'重新下载行情',run:i=>onMarketFill(asset.id,i.start,i.end)}:null);
        const info=disclosure(parent,'asset:'+asset.id,'来源与校验详情');info.append(el('p',asset.id,'hint'));for(const warning of c.warnings||[])info.append(el('p',typeof warning==='string'?warning:JSON.stringify(warning),'hint'));
      }
      for(const group of groupAssets(assets)){
        const section=el('section',undefined,'timeline-security');section.append(el('h3',(group.name&&group.name!==group.symbol?group.name+' · ':'')+group.symbol),el('span','推荐数据','status'));host.append(section);assetRows(section,group.recommended);
        if(group.alternatives.length){const history=disclosure(section,'symbol:'+group.symbol,'其他与历史版本（'+group.alternatives.length+'）');for(const asset of group.alternatives){const version=disclosure(history,'history:'+asset.id,(asset.start||'—')+' 至 '+(asset.end||'—'));assetRows(version,asset);}}
      }
      if(!assets.length)host.append(el('p','暂无证券行情版本。','hint'));
    }
    return {render};
  }
  const api={create,scaleSegment,groupAssets};root.CoverageTimeline=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
