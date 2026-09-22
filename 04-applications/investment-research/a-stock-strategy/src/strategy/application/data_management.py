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

    def _foundation(self):
        """分别读取指数和广度，不把指数末日误当成广度末日。"""
        folder = self.root/'data'/'real'
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
            if path.exists(): manifest = json.loads(path.read_text())
        except (ValueError, OSError) as exc:
            errors.append(f'基线清单不可用：{exc}')
        descriptor = dict(id='real', name='现有市场研究基线', adjustment=manifest.get('adjustment'),
                          index_start=None,index_end=None,breadth_start=None,breadth_end=None,
                          calendar_status='由现有指数日期观察，尚无独立交易日历服务', errors=errors)
        for prefix, frame in [('index',index),('breadth',breadth)]:
            if not frame.empty:
                descriptor[prefix+'_start'] = pd.Timestamp(frame.date.min()).date().isoformat()
                descriptor[prefix+'_end'] = pd.Timestamp(frame.date.max()).date().isoformat()
        return descriptor, index, breadth

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
        foundation = self._foundation()
        errors = list(foundation[0]['errors'])
        assets = []
        # 各资产隔离处理：一份坏文件不使整个数据页面失效。
        for folder in sorted((self.root/'data').glob('asset_*')):
            if not folder.is_dir(): continue
            try:
                item = detail_asset(self.root,folder.name)
                item.pop('preview',None)
                item.pop('manifest',None)
                item['readiness'] = self._readiness(item,foundation)
                assets.append(item)
            except (ValueError,OSError,KeyError) as exc:
                errors.append(f'{folder.name}：{exc}')
        try: legacy = [d for d in datasets(self.root) if not d['sample']]
        except (ValueError,OSError,KeyError) as exc:
            legacy = []
            errors.append(f'旧研究版本目录不可用：{exc}')
        return dict(today=today_cn().isoformat(), assets=assets, foundations=[foundation[0]], legacy_versions=legacy, errors=errors)

    def detail(self, identifier):
        item = detail_asset(self.root,identifier)
        item['readiness'] = self._readiness(item,self._foundation())
        return item

    def prepare_research(self, identifier):
        """显式准备共同覆盖的研究版本；源资产和旧任务永不修改。"""
        asset = self.detail(identifier)
        ready = asset['readiness']
        if ready['status']=='blocked':
            raise UserError('DATA_COVERAGE_INCOMPLETE','；'.join(ready['reasons']))
        request = dict(symbol=asset['symbol'],start=ready['start'],end=ready['end'])
        repository = LocalDatasetRepository(self.root)
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
