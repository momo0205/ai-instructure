"""Cumulative, conflict-aware coverage; all calendar evidence stays explicit."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import uuid
import pandas as pd
from strategy.market_data.csv import CsvMarketDataProvider, REQUIRED_MARKET_COLUMNS
from strategy.market_data.breadth import load_breadth
from strategy.validation import UserError


def _dates(values):
    return {pd.Timestamp(value).date().isoformat() for value in values}


def segments(dates, calendar=None, *, closed_dates=()):
    """Group contiguous sessions, never bridge an unexplained weekday gap."""
    days=sorted(_dates(dates))
    if not days: return []
    expected=sorted(_dates(calendar) if calendar is not None else
                    _dates(pd.bdate_range(days[0],days[-1]))-set(closed_dates))
    positions={day:i for i,day in enumerate(sorted(set(expected)|set(days)))}
    result=[]
    for day in days:
        if result and positions[day]==positions[result[-1]['end']]+1:
            result[-1].update(end=day,days=result[-1]['days']+1)
        else: result.append(dict(start=day,end=day,days=1))
    return result


class CoverageIndex:
    # Cache validated components across requests. Stat keys cover CSV and manifest;
    # a changed manifest must invalidate even when the table itself is unchanged.
    _cache={}

    def __init__(self, root, extra_folders=()):
        self.root=Path(root).resolve()
        self.errors=[]; self.conflicts=[]; self.sources=[]; self.closed_dates=set()
        frames={'index':[],'breadth':[]}
        folders=[self.root/'data'/'real']+sorted(
            p for p in (self.root/'data').glob('foundation_*')
            if re.fullmatch(r'foundation_[0-9a-f]+',p.name))
        folders+=list(map(Path,extra_folders))
        observed=set(); provenance={}
        for folder in dict.fromkeys(folders):
            if not folder.is_dir(): continue
            for kind,file,name,field in [('index','market.csv','market_manifest.json','market_sha256'),
                                          ('breadth','breadth.csv','manifest.json','breadth_sha256')]:
                if not (folder/file).exists() and not (folder/name).exists(): continue
                try:
                    frame,manifest,source=self._read(folder,kind,file,name,field)
                    if manifest.get('coverage_snapshot'): continue
                    observed |= _dates(frame.date)
                    if kind=='breadth':
                        if manifest.get('source')!='tushare.daily' or manifest.get('universe')!='SH_SZ_BJ' or not set(frame.source).issubset({'tushare.daily'}):
                            raise ValueError('incompatible breadth source/universe (requires tushare.daily / SH_SZ_BJ)')
                        self.closed_dates |= _dates(manifest.get('empty_dates',[]))
                    frames[kind].append((frame,str(folder.resolve())))
                    # Aggregate manifests point back to external original evidence.
                    for item in manifest.get('sources') or [source]:
                        key=item['path']
                        existing=provenance.setdefault(key,dict(item,hashes={}))
                        existing['hashes'].update(item.get('hashes',{}))
                        existing.setdefault('manifests',{}).update(item.get('manifests',{}))
                except Exception as exc:
                    self.errors.append(f'{folder.name}/{name}: {exc}')
        self.closed_dates-=observed
        self.closed_dates={d for d in self.closed_dates if pd.Timestamp(d).weekday()<5}
        self.sources=list(provenance.values())
        self.index=self._merge(frames['index'],'index',['open','high','low','close'])
        self.breadth=self._merge(frames['breadth'],'breadth',['declining_count','total_count'])

    @classmethod
    def _read(cls,folder,kind,file,name,field):
        paths=[folder/file,folder/name]
        manifest=json.loads(paths[1].read_text())
        if not isinstance(manifest,dict): raise ValueError('manifest must be an object')
        raw_paths=[]
        if kind=='breadth' and manifest.get('empty_dates') and manifest.get('raw_sha256') is not None:
            raw=Path(manifest.get('raw_dir',''))
            if not raw.is_absolute():
                raw=(folder if manifest.get('raw_dir_base')=='dataset_root' else folder.parent.parent)/raw
            raw_paths=[raw/(day+'.csv') for day in manifest['empty_dates'] if isinstance(day,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',day)]
        watched=paths+raw_paths
        state=tuple((p.stat().st_mtime_ns,p.stat().st_size) for p in watched)
        key=(str(folder.resolve()),kind)
        cached=cls._cache.get(key)
        if cached and cached[0]==state: return cached[1]
        manifest=json.loads(paths[1].read_text())
        if not isinstance(manifest,dict): raise ValueError('manifest must be an object')
        if manifest.get('coverage_snapshot'):
            return pd.DataFrame({'date':pd.to_datetime([])}),manifest,{}
        digest=hashlib.sha256(paths[0].read_bytes()).hexdigest()
        if field not in manifest and folder.name=='real':
            manifest=dict(manifest,warnings=list(manifest.get('warnings',[]))+[
                '历史 real 清单未记录表格哈希；本次已验证 CSV 并计算当前内容哈希，无法追溯验证旧内容。'])
        elif manifest.get(field)!=digest: raise ValueError('missing or mismatched table hash')
        if not manifest.get('source'): raise ValueError('missing source')
        if kind=='index':
            if manifest.get('adjustment')!='qfq': raise ValueError('incompatible index adjustment')
            frame=CsvMarketDataProvider(paths[0]).load()
            frame=frame[frame.symbol=='000001.SH'].copy()
        else:
            try: frame=load_breadth(paths[0])
            except ValueError:
                frame=pd.read_csv(paths[0])
                if not frame.empty or not {'date','declining_count','total_count','source'}.issubset(frame.columns): raise
                frame['date']=pd.to_datetime(frame.date)
            for day in manifest.get('empty_dates',[]):
                if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day) or pd.Timestamp(day).weekday()>=5:
                    raise ValueError('invalid observed closure date')
                if not manifest.get('start') or not manifest.get('end') or not manifest['start']<=day<=manifest['end']:
                    raise ValueError('observed closure outside declared request')
            for path in raw_paths:
                if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['raw_sha256'].get(path.stem):
                    raise ValueError('observed closure raw evidence hash mismatch')
                try: empty=pd.read_csv(path).empty
                except pd.errors.EmptyDataError: empty=True
                if not empty: raise ValueError('observed closure has nonempty raw evidence')
        if state!=tuple((p.stat().st_mtime_ns,p.stat().st_size) for p in watched):
            raise ValueError('source changed during validation')
        source=dict(path=str(folder.resolve()),dataset=folder.name,hashes={file:digest,name:hashlib.sha256(paths[1].read_bytes()).hexdigest()},manifests={name:{k:v for k,v in manifest.items() if k!='sources'}})
        result=(frame,manifest,source)
        cls._cache[key]=(state,result)
        return result

    def _merge(self,items,kind,columns):
        if not items:
            columns=REQUIRED_MARKET_COLUMNS if kind=='index' else ['date','declining_count','total_count','source']
            frame=pd.DataFrame(columns=columns)
            frame['date']=pd.to_datetime(frame.date)
            return frame
        combined=pd.concat([frame.assign(_coverage_source=source) for frame,source in items],ignore_index=True)
        # Determine conflicting values in one vectorized pass; ordinary dates
        # require no Python group loop on every timeline request.
        variants=combined[['date',*columns]].drop_duplicates()
        conflicting=set(variants.loc[variants.date.duplicated(keep=False),'date'])
        for date,group in combined[combined.date.isin(conflicting)].groupby('date',sort=True):
            self.conflicts.append(dict(date=date.date().isoformat(),kind=kind,sources=sorted(set(group._coverage_source))))
        return (combined[~combined.date.isin(conflicting)].drop_duplicates('date')
                .sort_values('date').drop(columns='_coverage_source').reset_index(drop=True))

    def summary(self):
        index=_dates(self.index.date); breadth=_dates(self.breadth.date); all_dates=index|breadth
        return dict(start=min(all_dates) if all_dates else None,end=max(all_dates) if all_dates else None,
                    index=segments(index,closed_dates=self.closed_dates),breadth=segments(breadth,closed_dates=self.closed_dates),
                    common=segments(index&breadth,closed_dates=self.closed_dates),conflicts=self.conflicts,errors=self.errors,
                    calendar_status='observed_empty_responses_not_independent_calendar')

    def plan(self,start,end):
        start=pd.Timestamp(start).date().isoformat(); end=pd.Timestamp(end).date().isoformat()
        if start>end: raise ValueError('start must not exceed end')
        expected=_dates(pd.bdate_range(start,end))-self.closed_dates
        index=_dates(self.index.date); breadth=_dates(self.breadth.date)
        return dict(start=start,end=end,index_missing=segments(expected-index,closed_dates=self.closed_dates),
                    breadth_missing=segments(expected-breadth,closed_dates=self.closed_dates),
                    conflicts=[c for c in self.conflicts if start<=c['date']<=end],
                    reused_index_days=len(expected&index),reused_breadth_days=len(expected&breadth))

    def snapshot(self,start,end,identifier=None,*,reusable=False):
        plan=self.plan(start,end); start,end=plan['start'],plan['end']
        if plan['index_missing'] or plan['breadth_missing'] or plan['conflicts']:
            raise UserError('DATA_VALIDATION_FAILED','基础覆盖存在缺口或冲突，不能发布')
        index=self.index[self.index.date.between(start,end)].copy()
        breadth=self.breadth[self.breadth.date.between(start,end)].copy()
        # A reusable coverage update may fill one session, or retain only an
        # observed closure. Research snapshots still require two sessions.
        if (not reusable and len(index)<2) or _dates(index.date)!=_dates(breadth.date):
            raise UserError('DATA_VALIDATION_FAILED','基础数据需要至少两个完整交易日')
        identifier=identifier or uuid.uuid4().hex
        if not isinstance(identifier,str) or not re.fullmatch('[0-9a-f]+',identifier): raise ValueError('invalid foundation identifier')
        data=self.root/'data'; data.mkdir(parents=True,exist_ok=True)
        final=data/('foundation_'+identifier); stage=data/('.coverage_'+identifier)
        if final.exists(): raise ValueError('foundation already exists')
        stage.mkdir()
        try:
            index.to_csv(stage/'market.csv',index=False); breadth.to_csv(stage/'breadth.csv',index=False)
            warnings=list(dict.fromkeys([warning for source in self.sources for manifest in source.get('manifests',{}).values() for warning in manifest.get('warnings',[])]+[
                '全市场广度完整性未经独立验证；停牌证券可能不包含在每日截面中。',
                '休市仅依据已留存的空响应推断，未使用独立交易日历验证。']))
            common=dict(warnings=warnings,complete_universe_verified=False,
                        calendar_status='observed_empty_responses_not_independent_calendar',coverage_snapshot=not reusable,foundation_id=final.name,start=start,end=end,sources=self.sources,
                        coverage_dates=sorted(_dates(index.date)),empty_dates=sorted(d for d in self.closed_dates if start<=d<=end))
            for name,file,field,extra in [('market_manifest.json','market.csv','market_sha256',dict(source='cumulative.index',adjustment='qfq',symbols=['000001.SH'])),
                                          ('manifest.json','breadth.csv','breadth_sha256',dict(source='tushare.daily',universe='SH_SZ_BJ'))]:
                manifest=dict(common,**extra,**{field:hashlib.sha256((stage/file).read_bytes()).hexdigest()})
                (stage/name).write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
            stage.rename(final)
        except Exception:
            shutil.rmtree(stage,ignore_errors=True)
            raise
        return final.name
