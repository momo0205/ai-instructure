"""本地数据版本仓库：目录、校验、冻结与原子发布，不发起网络请求。"""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import hashlib
import json
import re
import shutil
import tomllib
import pandas as pd
from strategy.market_data.csv import CsvMarketDataProvider
from strategy.market_data.breadth import load_breadth


def verify_manifests(folder):
    """拒绝更新中或损坏的数据/清单组合；旧清单无哈希时不声称已验证。"""
    folder = Path(folder)
    for manifest_name, filename, field in (
        ('market_manifest.json', 'market.csv', 'market_sha256'),
        ('manifest.json', 'breadth.csv', 'breadth_sha256'),
    ):
        path = folder/manifest_name
        if path.is_file():
            manifest = json.loads(path.read_text())
            expected = manifest.get(field)
            if expected is not None and expected != hashlib.sha256((folder/filename).read_bytes()).hexdigest():
                raise ValueError(f'{filename} hash mismatch：数据正在更新或清单已过期，请重新下载后重试')


def datasets(project_root):
    """列出实际存在的数据集；样例数据始终明确标记。"""
    result = []
    managed = sorted(p.name for p in (Path(project_root)/'data').glob('managed_*') if p.is_dir())
    for name in ('real','mvp_sample', *managed):
        folder = Path(project_root)/'data'/name
        if not all((folder/f).is_file() for f in ('market.csv','breadth.csv')):
            continue
        verify_manifests(folder)
        market = CsvMarketDataProvider(folder/'market.csv').load()
        breadth = load_breadth(folder/'breadth.csv')
        index_calendar = market.loc[market.symbol == '000001.SH', 'date']
        if index_calendar.empty:
            continue
        config_path = Path(project_root)/'configs'/('real_breadth.toml' if name=='real' else 'mvp.toml')
        config = tomllib.loads(config_path.read_text()) if config_path.is_file() else {}
        provenance = config.get('metadata',{})
        market_manifest_path = folder/'market_manifest.json'
        market_manifest = json.loads(market_manifest_path.read_text()) if market_manifest_path.is_file() else {}
        market_source = market_manifest.get('source', config.get('data',{}).get('source','unknown'))
        warnings = list(market_manifest.get('warnings', provenance.get('warnings',['数据质量未经独立验证'])))
        # 旧快照保留原文及哈希；展示时注明历史能力说明，避免与当前目录矛盾。
        warnings = [w.replace('仅三只已验证 ETF 支持回测。', '此版本创建时仅开放 ETF；当前支持范围以标的目录为准。') for w in warnings]
        if name=='mvp_sample':
            warnings.insert(0,'合成样例，不代表真实市场表现')
        result.append(dict(id=name,name='真实市场数据' if name=='real' else '合成样例',start=index_calendar.min().date().isoformat(),end=index_calendar.max().date().isoformat(),symbols=sorted(market.symbol.unique().tolist()),source=sorted(breadth.source.unique().tolist()),market_source=market_source,adjustment=market_manifest.get('adjustment',config.get('data',{}).get('adjustment','unknown')),sample=name=='mvp_sample',warnings=warnings))
        from strategy.market_data.catalog import describe
        metadata = market_manifest.get('instruments', {})
        result[-1]['instruments'] = [dict(describe(symbol, metadata.get(symbol)),
            start=rows.date.min().date().isoformat(), end=rows.date.max().date().isoformat())
            for symbol, rows in market.groupby('symbol')]
        if name.startswith('managed_'):
            symbol = market_manifest.get('updated_symbol', '')
            result[-1]['name'] = f'行情版本 · {symbol} · {name[-8:]}'
    return result


@dataclass(frozen=True)
class PreparedDataset:
    """一次发布的暂存上下文；旧基线的摘要随新版本保留。"""
    identifier: str
    stage: Path
    hashes: dict
    old_manifest: dict
    adjustment: str


class DatasetRepository(Protocol):
    """下载编排所需的仓库接口；本轮仍以本地目录实现。"""
    def list(self) -> list[dict]: ...
    def prepare(self, identifier: str) -> PreparedDataset: ...
    def publish(self, prepared: PreparedDataset, request: dict, metadata: dict) -> str: ...


class LocalDatasetRepository:
    def __init__(self, root):
        self.root = Path(root)

    def list(self):
        return datasets(self.root)

    def prepare(self, identifier):
        """冻结基线并准备提供方输出目录，尚不暴露可回测版本。"""
        if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', identifier):
            raise ValueError('invalid dataset identifier')
        base = self.root/'data'/'real'
        verify_manifests(base)
        stage = self.root/'data'/('.download_'+identifier)
        stage.mkdir(parents=True)
        # 基线在复制前后必须稳定；发布只改新版本，绝不替换 data/real。
        names = ('market.csv','breadth.csv','manifest.json','market_manifest.json')
        hashes = {name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names if (base/name).is_file()}
        for name in hashes:
            shutil.copyfile(base/name, stage/name)
        if any(hashlib.sha256((base/name).read_bytes()).hexdigest()!=digest or hashlib.sha256((stage/name).read_bytes()).hexdigest()!=digest for name,digest in hashes.items()):
            raise ValueError('基线数据在复制时变化，请重试')
        verify_manifests(stage)
        old_manifest = json.loads((stage/'market_manifest.json').read_text()) if (stage/'market_manifest.json').exists() else {}
        config_path = self.root/'configs'/'real_breadth.toml'
        config = tomllib.loads(config_path.read_text()) if config_path.is_file() else {}
        # 清单优先于配置；缺少证据时禁止猜测复权方式，避免混合价格口径。
        adjustment = old_manifest.get('adjustment', config.get('data', {}).get('adjustment'))
        if adjustment not in ('none','qfq'):
            raise ValueError('基线复权方式未知，无法安全合并行情')
        download = stage/'download'
        download.mkdir()
        shutil.copyfile(stage/'breadth.csv', download/'breadth.csv')
        return PreparedDataset(identifier, stage, hashes, old_manifest, adjustment)

    def publish(self, prepared, request, metadata):
        """合并已下载文件并原子发布。调用方负责获取数据，仓库负责其合同。"""
        identifier, stage = prepared.identifier, prepared.stage
        hashes, old_manifest, adjustment = prepared.hashes, prepared.old_manifest, prepared.adjustment
        base, download = self.root/'data'/'real', stage/'download'
        if metadata.get('symbol') != request['symbol']:
            raise ValueError('证券元数据代码不匹配')
        downloaded_manifest = json.loads((download/'market_manifest.json').read_text())
        if not isinstance(downloaded_manifest.get('source'), str) or not downloaded_manifest['source'].strip():
            raise ValueError('下载清单缺少数据来源')
        if not isinstance(downloaded_manifest.get('market_sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', downloaded_manifest['market_sha256']):
            raise ValueError('下载清单缺少有效行情哈希')
        verify_manifests(download)
        if downloaded_manifest.get('adjustment') != adjustment:
            raise ValueError('下载行情复权方式与基线不一致')
        # 提供方可替换，因此仓库自己验证标准CSV，不信任适配器已校验的假设。
        CsvMarketDataProvider(download/'market.csv').load()
        incoming = pd.read_csv(download/'market.csv')
        existing = pd.read_csv(stage/'market.csv')
        expected = set(existing.loc[(existing.symbol=='000001.SH') & existing.date.between(request['start'],request['end']), 'date'])
        actual = set(incoming.loc[incoming.symbol==request['symbol'],'date'])
        if not expected or actual != expected:
            raise ValueError('目标证券与基线交易日不一致（可能停牌或上市时间不足），未发布')
        # 同一证券整段替换，避免不同时点前复权价格拼接造成虚假跳变。
        merged = pd.concat([existing[existing.symbol!=request['symbol']], incoming[incoming.symbol==request['symbol']]], ignore_index=True).sort_values(['date','symbol'])
        merged.to_csv(stage/'market.csv', index=False)
        if downloaded_manifest.get('raw_dir'):
            raw = Path(downloaded_manifest['raw_dir']).resolve()
            if not raw.is_dir() or not raw.is_relative_to(download.resolve()):
                raise ValueError('原始响应目录必须位于本次下载目录内')
            # 指向暂存路径的绝对链接在原子重命名后会失效，证据只接受实体文件。
            if any(path.is_symlink() for path in raw.rglob('*')):
                raise ValueError('原始响应不允许符号链接')
            raw_hashes = downloaded_manifest.get('raw_sha256')
            if not isinstance(raw_hashes, dict) or not raw_hashes:
                raise ValueError('原始响应缺少内容哈希')
            for name, digest in raw_hashes.items():
                path = (raw/name).resolve()
                if not path.is_relative_to(raw) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError('原始响应文件或哈希不匹配')
            downloaded_manifest['raw_dir'] = str(raw.relative_to(stage.resolve()))
        # 两份下载清单使用同一相对路径，原子发布重命名后仍能找到原始响应。
        downloaded_manifest['raw_dir_base'] = 'dataset_root'
        (download/'market_manifest.json').write_text(json.dumps(downloaded_manifest, ensure_ascii=False, indent=2))
        parent_provenance = {key: old_manifest[key] for key in ('raw_dir', 'raw_sha256') if key in old_manifest}
        if parent_provenance.get('raw_dir'):
            parent_path = Path(parent_provenance['raw_dir'])
            # 旧 CLI 使用 --output data/real 时记录项目根相对路径，不能再次拼 data/real。
            # 其他未声明基准的旧相对路径保留原文，避免猜测一个错误的审计位置。
            if parent_path.is_absolute():
                parent_provenance['raw_dir_base'] = 'absolute'
            elif old_manifest.get('raw_dir_base') == 'dataset_root':
                parent_provenance['raw_dir'] = str((base/parent_path).resolve())
                parent_provenance['raw_dir_base'] = 'absolute'
            elif parent_path.parts[:2] == ('data', 'real') or old_manifest.get('raw_dir_base') == 'project_root':
                parent_provenance['raw_dir'] = str((self.root/parent_path).resolve())
                parent_provenance['raw_dir_base'] = 'absolute'
            else:
                parent_provenance['raw_dir_base'] = 'unknown'
        manifest = dict(old_manifest, source='managed baseline + '+downloaded_manifest.get('source', 'unknown'), adjustment=adjustment,
                        market_sha256=hashlib.sha256((stage/'market.csv').read_bytes()).hexdigest(),
                        parent_dataset='real', parent_hashes=hashes, download=downloaded_manifest,
                        parent_provenance=parent_provenance,
                        instruments={**old_manifest.get('instruments', {}), request['symbol']:metadata}, updated_symbol=request['symbol'],
                        symbols=sorted(merged.symbol.unique().tolist()), rows=len(merged),
                        symbol_sources={symbol: downloaded_manifest if symbol==request['symbol'] else {'dataset':'real','market_sha256':hashes['market.csv']} for symbol in merged.symbol.unique()},
                        warnings=list(old_manifest.get('warnings', []))+list(downloaded_manifest.get('warnings', []))+['新增证券只覆盖下载区间；同代码旧行情整段移除，避免前复权基准拼接。',
                            '支持范围由当前交易规则目录决定。基线与新增行情分别保留来源；历史基线量额单位可能未经验证，成交量因子结果须谨慎解读。'])
        # 混合版本不能把某一次下载的量额单位冒充为整个数据集的统一声明。
        manifest.pop('volume_unit', None)
        manifest.pop('amount_unit', None)
        manifest.pop('raw_dir', None)
        manifest.pop('raw_sha256', None)
        # 混合版本的供应商信息按标的记录，不继承旧供应商的整体入口。
        manifest.pop('source_url', None)
        manifest.pop('raw_dir_base', None)
        (stage/'market_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        verify_manifests(stage)
        CsvMarketDataProvider(stage/'market.csv').load()
        dataset_id = 'managed_'+identifier
        stage.rename(self.root/'data'/dataset_id)
        return dataset_id
