"""数据工作台：行情资产与当前市场触发策略的依赖分开检查。"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from uuid import uuid4
import hashlib
import json
import shutil
import pandas as pd
from strategy.market_data.assets import detail_asset
from strategy.market_data.repository import datasets, LocalDatasetRepository, verify_manifests
from strategy.market_data.catalog import describe
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.market_data.breadth import load_breadth
from strategy.validation import UserError


def today_cn():
    return datetime.now(ZoneInfo('Asia/Shanghai')).date()


class DataManagementService:
    def __init__(self, root):
        self.root = Path(root)
        from strategy.market_data.coverage import CoverageIndex
        self.coverage_index = CoverageIndex(self.root)

    def _foundation(self, identifier='real'):
        """分别读取指数和广度，不把指数末日误当成广度末日。"""
        folder = self.root/'data'/identifier
        index, breadth, errors = pd.DataFrame(), pd.DataFrame(), []
        try:
            verify_manifests(folder)
            if (folder/'market.csv').is_file():
                market = CsvMarketDataProvider(folder/'market.csv').load()
                index = market[market.symbol == '000001.SH'].copy()
            if (folder/'breadth.csv').is_file():
                breadth = load_breadth(folder/'breadth.csv')
        except (ValueError, OSError, KeyError) as exc:
            # 损坏基线不能用于准备研究，但不挡住独立行情资产浏览与下载。
            errors.append(f'基础数据不可用：{exc}')
            index, breadth = pd.DataFrame(), pd.DataFrame()
        manifest = {}
        try:
            path = folder/'market_manifest.json'
            if path.exists():
                manifest = json.loads(path.read_text())
                if not isinstance(manifest, dict):
                    manifest = {}
                    raise ValueError('数据清单必须为对象')
        except (ValueError, OSError) as exc:
            errors.append(f'基线清单不可用：{exc}')
        descriptor = dict(id=identifier, name='现有市场研究基线' if identifier=='real' else '市场基础版本 · '+identifier[-8:], adjustment=manifest.get('adjustment'),
                          index_start=None,index_end=None,breadth_start=None,breadth_end=None,
                          calendar_status='由现有指数日期观察，尚无独立交易日历服务', errors=errors)
        for prefix, frame in [('index',index),('breadth',breadth)]:
            if not frame.empty:
                descriptor[prefix+'_start'] = pd.Timestamp(frame.date.min()).date().isoformat()
                descriptor[prefix+'_end'] = pd.Timestamp(frame.date.max()).date().isoformat()
        return descriptor, index, breadth

    def _foundations(self):
        names = ['real'] + sorted(p.name for p in (self.root/'data').glob('foundation_*') if p.is_dir())
        return [self._foundation(name) for name in names]

    def _select_readiness(self, asset, foundations=None):
        from strategy.application.asset_coverage import asset_coverage
        asset['coverage'] = asset_coverage(self.root,asset,self.coverage_index,(today_cn()-timedelta(days=1)).isoformat())
        # 旧导入的非标准来源保留原来单版本验证；生产标准来源统一使用累计覆盖。
        if not self.coverage_index.breadth.empty or self.coverage_index.conflicts:
            intervals=asset['coverage']['research']
            if not intervals:
                return dict(status='blocked',start=None,end=None,foundation_id=None,reasons=['累计基础数据与行情没有连续两个交易日的共同覆盖；请查看时间轴中的缺口或冲突'])
            best=max(intervals,key=lambda x:x['days'])
            return dict(status='ready' if best['start']==asset['start'] and best['end']==asset['end'] else 'partial',
                        start=best['start'],end=best['end'],foundation_id='cumulative',
                        reasons=[] if len(intervals)==1 else ['存在多个独立可研究区间，默认选择最长区间；可在时间轴选择其他区间'])
        candidates = []
        for foundation in foundations or self._foundations():
            ready = self._readiness(asset, foundation)
            ready['foundation_id'] = foundation[0]['id']
            days = 0 if ready['status']=='blocked' else len(foundation[1].loc[foundation[1].date.between(ready['start'],ready['end'])])
            candidates.append((days, ready))
        ready=max(candidates, key=lambda item:item[0])[1]
        if ready['status']!='blocked':
            asset['coverage']['research']=[dict(start=ready['start'],end=ready['end'],days=max(candidates,key=lambda item:item[0])[0])]
        return ready

    def _readiness(self, asset, foundation):
        desc, index, breadth = foundation
        reasons = list(desc['errors'])
        instrument = describe(asset['symbol'], asset)
        if not instrument['backtest_supported']:
            reasons.append(instrument['reason'])
        if index.empty: reasons.append('缺少可用上证指数行情')
        if breadth.empty: reasons.append('缺少可用全市场广度')
        if asset['adjustment'] != desc['adjustment']:
            reasons.append('行情与现有研究基线复权口径不同，不能直接组装')
        if reasons:
            return dict(status='blocked',start=None,end=None,reasons=reasons)
        # 只用已完成的历史日期；今天的接口返回值尚未确认是终盘数据。
        start = max(asset['start'], desc['index_start'], desc['breadth_start'], instrument['backtest_start'] or asset['start'])
        end = min(asset['end'], desc['index_end'], desc['breadth_end'], (today_cn()-timedelta(days=1)).isoformat())
        if start > end:
            return dict(status='blocked', start=None, end=None, reasons=[
                f"行情与指数/广度没有共同研究区间；指数截至 {desc['index_end']}，广度截至 {desc['breadth_end']}"])
        market = CsvMarketDataProvider(self.root/'data'/asset['id']/'market.csv').load()
        dates = set(market.loc[(market.symbol==asset['symbol']) & market.date.between(start,end),'date'])
        calendar = set(index.loc[index.date.between(start,end),'date'])
        available_breadth = set(breadth.loc[breadth.date.between(start,end),'date'])
        if len(calendar)<2: reasons.append('共同区间不足两个交易日')
        if calendar != available_breadth: reasons.append('共同区间内广度日期不完整')
        if dates != calendar: reasons.append('共同区间内行情与指数日期不一致；缺口不能自动视为停牌或填充价格')
        if reasons: return dict(status='blocked',start=None,end=None,reasons=reasons)
        actual_start, actual_end = min(dates).date().isoformat(), max(dates).date().isoformat()
        partial = actual_start > asset['start'] or actual_end < asset['end']
        return dict(status='partial' if partial else 'ready',start=actual_start,end=actual_end,
                    reasons=[f'仅共同区间可运行；其余日期仍缺少指数、广度或终盘确认'] if partial else [])

    def catalog(self):
        foundations = self._foundations()
        errors = [f"{f[0]['id']}：{error}" for f in foundations for error in f[0]['errors']]
        assets = []
        # 各资产隔离处理：一份坏文件不使整个数据页面失效。
        for folder in sorted((self.root/'data').glob('asset_*')):
            if not folder.is_dir(): continue
            try:
                item = detail_asset(self.root,folder.name)
                item.pop('preview',None)
                item.pop('manifest',None)
                item['readiness'] = self._select_readiness(item,foundations)
                assets.append(item)
            except (ValueError,OSError,KeyError) as exc:
                errors.append(f'{folder.name}：{exc}')
        try: legacy = [d for d in datasets(self.root) if not d['sample']]
        except (ValueError,OSError,KeyError) as exc:
            legacy = []
            errors.append(f'旧研究版本目录不可用：{exc}')
        timeline_assets=list(assets)
        from strategy.application.asset_coverage import asset_coverage
        for version in legacy:
            for instrument in version.get('instruments',[]):
                if not instrument.get('backtest_supported'): continue
                item=dict(instrument,id=version['id']+'::'+instrument['symbol'],dataset_id=version['id'],adjustment=version['adjustment'])
                try:
                    item['coverage']=asset_coverage(self.root,item,self.coverage_index,(today_cn()-timedelta(days=1)).isoformat())
                    timeline_assets.append(item)
                except (ValueError,OSError,KeyError) as exc:
                    errors.append(f"{item['id']}：{exc}")
        return dict(timeline_assets=timeline_assets,coverage=self.coverage_index.summary(),today=today_cn().isoformat(), assets=assets, foundations=[f[0] for f in foundations], legacy_versions=legacy, errors=errors)

    def detail(self, identifier):
        item = detail_asset(self.root,identifier)
        item['readiness'] = self._select_readiness(item)
        return item

    def prepare_research(self, identifier, *, start=None, end=None):
        """显式准备共同覆盖的研究版本；源资产和旧任务永不修改。"""
        return self._prepare_asset(self.detail(identifier),start=start,end=end)

    def prepare_legacy(self, dataset_id, symbol, *, start=None, end=None):
        """旧研究版本也通过同一组装流程，不能将累计覆盖误用于旧冻结输入。"""
        version=next((v for v in datasets(self.root) if v['id']==dataset_id and not v['sample']),None)
        if version is None: raise UserError('INVALID_REQUEST','研究数据版本不存在')
        instrument=next((i for i in version['instruments'] if i['symbol']==symbol and i['backtest_supported']),None)
        if instrument is None: raise UserError('INVALID_REQUEST','该版本未包含可研究证券')
        asset=dict(instrument,id=dataset_id,dataset_id=dataset_id,adjustment=version['adjustment'],source=version['market_source'],warnings=version['warnings'])
        asset['readiness']=self._select_readiness(asset)
        return self._prepare_asset(asset,start=start,end=end)

    def _prepare_asset(self, asset, *, start=None, end=None):
        identifier=asset['id']
        ready = asset['readiness']
        if ready['status']=='blocked':
            raise UserError('DATA_COVERAGE_INCOMPLETE','；'.join(ready['reasons']))
        if start is not None or end is not None:
            try:
                valid=isinstance(start,str) and isinstance(end,str) and start<end and any(span['start']<=start<=end<=span['end'] for span in asset['coverage']['research'])
                if not valid: raise ValueError
                if pd.Timestamp(start).date().isoformat()!=start or pd.Timestamp(end).date().isoformat()!=end: raise ValueError
            except (ValueError,TypeError):
                raise UserError('DATA_COVERAGE_INCOMPLETE','所选区间不在连续可研究覆盖内') from None
            ready=dict(ready,start=start,end=end)
        request = dict(symbol=asset['symbol'],start=ready['start'],end=ready['end'])
        baseline=ready['foundation_id']
        if baseline=='cumulative':
            baseline=self.coverage_index.snapshot(ready['start'],ready['end'])
        repository = LocalDatasetRepository(self.root, baseline_id=baseline)
        prepared = repository.prepare(uuid4().hex)
        try:
            source = self.root/'data'/identifier
            # 再核验源文件，避免下载/文件变化让准备结果与预览不一致。
            verify_manifests(source)
            frame = CsvMarketDataProvider(source/'market.csv').load()
            frame = frame[frame.date.between(request['start'],request['end'])]
            destination = prepared.stage/'download'
            frame.to_csv(destination/'market.csv',index=False)
            original = json.loads((source/'market_manifest.json').read_text())
            manifest = dict(source=asset['source'],adjustment=asset['adjustment'],
                market_sha256=hashlib.sha256((destination/'market.csv').read_bytes()).hexdigest(),
                warnings=asset.get('warnings',[]),asset_reference=dict(id=identifier,
                    original_dataset_root=str(source.resolve()), manifest=original,
                    raw_evidence='external_in_asset_directory'))
            (destination/'market_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
            dataset_id = repository.publish(prepared,request,dict(symbol=asset['symbol'],name=asset['name'],kind=asset['kind']))
        except Exception:
            shutil.rmtree(prepared.stage,ignore_errors=True)
            raise
        return dict(dataset_id=dataset_id,start=ready['start'],end=ready['end'])
