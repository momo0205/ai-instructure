/* Select a single immutable price source; never combine adjustment histories. */
(function(root){
'use strict';
const research=a=>a.coverage?.research||(['ready','partial'].includes(a.readiness?.status)?[{start:a.readiness.start,end:a.readiness.end}]:[]);
const span=a=>research(a).reduce((n,i)=>n+Math.max(0,Date.parse(i.end)-Date.parse(i.start)+86400000),0);
const legacy=a=>String(a.id).includes('::');
function compare(a,b){return Number(!research(a).length)-Number(!research(b).length)||String(b.end||'').localeCompare(String(a.end||''))||span(b)-span(a)||Number(legacy(a))-Number(legacy(b))||String(b.created_at||'').localeCompare(String(a.created_at||''))||String(a.id).localeCompare(String(b.id));}
function groupAssets(assets,query=''){
 const groups=new Map(),needle=query.trim().toLowerCase();
 for(const a of assets||[]){if(needle&&!`${a.symbol} ${a.name||''}`.toLowerCase().includes(needle))continue;const key=a.symbol||a.id;if(!groups.has(key))groups.set(key,{symbol:key,name:a.name||'',versions:[]});groups.get(key).versions.push(a);}
 return [...groups.values()].map(g=>{const seen=new Set();g.versions.sort(compare);g.versions=g.versions.filter(a=>{const key=a.market_sha256?`${a.adjustment||''}:${a.start}:${a.end}:${a.market_sha256}`:null;if(!key)return true;if(seen.has(key))return false;seen.add(key);return true;});g.recommended=g.versions[0];g.alternatives=g.versions.slice(1);return g;}).sort((a,b)=>a.symbol.localeCompare(b.symbol));
}
const api={groupAssets,research};root.DataVersions=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
