"""把已有证券快照组合为独立研究版本；不下载、不拼接同一证券的价格历史。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4
import pandas as pd
from strategy.market_data.repository import datasets, verify_manifests
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.market_data.breadth import load_breadth
from strategy.validation import UserError


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompositionService:
    def __init__(self, root):
        self.root = Path(root)

    def _prepare(self, request, stage, *, minimum_members=2):
        if not isinstance(request,dict) or set(request)!={'base_dataset_id','members'}:
            raise UserError('INVALID_REQUEST','请选择基线及证券来源版本')
        catalog={d['id']:d for d in datasets(self.root)}
        members=request['members']
        if not isinstance(members,list) or not minimum_members<=len(members)<=20 or any(not isinstance(m,dict) or set(m)!={'dataset_id','symbol'} or not all(isinstance(v,str) for v in m.values()) for m in members):
            raise UserError('INVALID_REQUEST','请选择 2 至 20 只证券，每只指定一个来源版本')
        if len({m['symbol'] for m in members})!=len(members):
            raise UserError('INVALID_REQUEST','同一证券只能选择一个来源版本，请取消重复选择')
        base=request['base_dataset_id']
        ids=[base]+[m['dataset_id'] for m in members]
        if any(not isinstance(i,str) or i not in catalog or catalog[i]['sample'] for i in ids):
            raise UserError('INVALID_REQUEST','仅支持目录中已准备的真实数据版本，不能混入合成样例')
        for m in members:
            if not any(i['symbol']==m['symbol'] and i['backtest_supported'] for i in catalog[m['dataset_id']]['instruments']):
                raise UserError('INVALID_REQUEST',f"{m['symbol']} 不属于所选版本的可回测证券")
        sources={}; hashes={}; manifests={}; markets={}; breadths={}
        # 每个来源只冻结一次；复制前后核对，随后只读取冻结文件。
        for identifier in sorted(set(ids)):
            source=self.root/'data'/identifier;target=stage/'sources'/identifier
            target.mkdir(parents=True)
            names=[n for n in ('market.csv','breadth.csv','market_manifest.json','manifest.json') if (source/n).is_file()]
            hashes[identifier]={n:digest(source/n) for n in names}
            for name in names:shutil.copyfile(source/name,target/name)
            if any(digest(source/n)!=h or digest(target/n)!=h for n,h in hashes[identifier].items()):
                raise UserError('DATA_VALIDATION_FAILED','来源在读取时发生变化，请刷新后重试')
            verify_manifests(target)
            manifest=json.loads((target/'market_manifest.json').read_text()) if (target/'market_manifest.json').exists() else {}
            manifests[identifier]=manifest
            sources[identifier]=target
            markets[identifier]=CsvMarketDataProvider(target/'market.csv').load()
            breadths[identifier]=load_breadth(target/'breadth.csv')
        adjustments={manifests[i].get('adjustment') for i in ids}
        if len(adjustments)!=1 or next(iter(adjustments)) not in ('qfq','none'):
            raise UserError('DATA_VALIDATION_FAILED','来源复权方式未知或不一致，不能创建组合')
        index=markets[base].query("symbol == '000001.SH'")
        pieces=[markets[m['dataset_id']].loc[markets[m['dataset_id']].symbol==m['symbol']].copy() for m in members]
        start=max([index.date.min()]+[p.date.min() for p in pieces])
        end=min([index.date.max()]+[p.date.max() for p in pieces])
        index=index[index.date.between(start,end)].reset_index(drop=True)
        calendar=set(index.date)
        if len(calendar)<2:
            raise UserError('DATA_COVERAGE_INCOMPLETE','证券与基线没有至少两个共同交易日')
        breadth=breadths[base];breadth=breadth[breadth.date.between(start,end)].reset_index(drop=True)
        if set(breadth.date)!=calendar:
            raise UserError('DATA_COVERAGE_INCOMPLETE','基线市场广度不完整')
        for identifier in set(ids):
            other=markets[identifier];other=other[(other.symbol=='000001.SH')&other.date.between(start,end)].reset_index(drop=True)
            other_breadth=breadths[identifier];other_breadth=other_breadth[other_breadth.date.between(start,end)].reset_index(drop=True)
            # 拒绝基线不同，不能让同一组合的触发信号取决于某个隐式来源。
            try:
                pd.testing.assert_frame_equal(index,other,check_dtype=False,check_exact=True)
                pd.testing.assert_frame_equal(breadth,other_breadth,check_dtype=False,check_exact=True)
            except AssertionError:
                raise UserError('DATA_VALIDATION_FAILED',f'来源 {identifier} 的指数或市场广度与所选基线不一致')
        trimmed=[]
        for m,piece in zip(members,pieces):
            piece=piece[piece.date.between(start,end)]
            if set(piece.date)!=calendar:
                raise UserError('DATA_COVERAGE_INCOMPLETE',f"{m['symbol']} 在共同区间内存在行情缺口，未删除日期或填充价格")
            trimmed.append(piece)
        warnings=list(dict.fromkeys(w for i in sorted(set(ids)) for w in catalog[i]['warnings']))
        warnings.append('来源清单按原样归档；原始下载响应及嵌套证据仍位于原数据版本，追溯时使用 original_dataset_root，不能按归档目录重解释相对路径。')
        warnings.append('组合版本仅保留共同覆盖区间；各证券保留各自复权基准与来源，不拼接同代码历史；成交状态及量额单位限制仍适用。')
        summary=dict(base_dataset_id=base,members=members,start=start.date().isoformat(),end=end.date().isoformat(),sessions=len(calendar),adjustment=next(iter(adjustments)),source_hashes=hashes,warnings=warnings)
        summary['preview_digest']=hashlib.sha256(json.dumps(summary,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        merged=pd.concat([index,*trimmed],ignore_index=True).sort_values(['date','symbol'])
        merged.to_csv(stage/'market.csv',index=False);breadth.to_csv(stage/'breadth.csv',index=False)
        instruments={m['symbol']:manifests[m['dataset_id']].get('instruments',{}).get(m['symbol'],next(i for i in catalog[m['dataset_id']]['instruments'] if i['symbol']==m['symbol'])) for m in members}
        manifest=dict(source='composed frozen datasets',adjustment=summary['adjustment'],created_at=datetime.now(timezone.utc).isoformat(),
            market_sha256=digest(stage/'market.csv'),composition=summary,instruments=instruments,warnings=warnings,
            symbol_sources={m['symbol']:dict(dataset=m['dataset_id'],hashes=hashes[m['dataset_id']],source_manifest=f"sources/{m['dataset_id']}/market_manifest.json",original_dataset_root=str((self.root/'data'/m['dataset_id']).resolve()),raw_evidence='external_to_composition') for m in members})
        (stage/'market_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        (stage/'manifest.json').write_text(json.dumps(dict(breadth_sha256=digest(stage/'breadth.csv'),source_dataset=base,parent_hashes=hashes[base]),ensure_ascii=False,indent=2))
        verify_manifests(stage);CsvMarketDataProvider(stage/'market.csv').load()
        return summary

    def _run(self, payload, publish):
        if not isinstance(payload,dict):raise UserError('INVALID_REQUEST','组合请求格式错误')
        request=dict(payload);expected=request.pop('preview_digest',None)
        if publish and not isinstance(expected,str):
            raise UserError('INVALID_REQUEST','请先检查组合，再创建版本')
        with tempfile.TemporaryDirectory(prefix='.compose_',dir=self.root/'data') as temporary:
            stage=Path(temporary)/'dataset';stage.mkdir()
            summary=self._prepare(request,stage)
            if not publish:return summary
            if expected!=summary['preview_digest']:
                raise UserError('DATA_VALIDATION_FAILED','组合选择或来源自检查后发生变化，请重新检查组合')
            identifier='managed_'+uuid4().hex
            # 只在完整验证后一次性发布，失败的暂存目录由上下文回收。
            stage.rename(self.root/'data'/identifier)
            return dict(summary,dataset_id=identifier)

    def preview(self,payload):return self._run(payload,False)
    def create(self,payload):return self._run(payload,True)
