"""用本地提供方验证模块合同；不请求外部行情服务。"""
import json
import hashlib
import shutil
from pathlib import Path

import pandas as pd
import pytest

from strategy import workbench

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    base = tmp_path/'data'/'real'
    shutil.copytree(ROOT/'data'/'mvp_sample', base)
    (base/'market_manifest.json').write_text('{"adjustment":"none"}')
    return tmp_path


class OtherProvider:
    def __init__(self, root):
        self.root = root

    def resolve(self, symbol):
        return {'symbol': symbol, 'name': '协鑫能科', 'kind': 'stock'}

    def download(self, start, end, output_dir, symbols, adjustment):
        rows = pd.read_csv(self.root/'data'/'real'/'market.csv')
        rows = rows[rows.symbol == '588000.SH'].assign(symbol=symbols[0])
        rows = rows[rows.date.between(start, end)]
        rows.to_csv(output_dir/'market.csv', index=False)
        (output_dir/'market_manifest.json').write_text(json.dumps({'source': 'other-provider', 'adjustment': adjustment,
            'market_sha256': hashlib.sha256((output_dir/'market.csv').read_bytes()).hexdigest(),
            'warnings': ['provider-specific limitation']}))


def test_replace_provider_without_changing_download_or_backtest(project):
    from strategy.instruments import DownloadManager
    from strategy.dataset_repository import LocalDatasetRepository
    repository = LocalDatasetRepository(project)
    (project/'data'/'real'/'market_manifest.json').write_text(json.dumps({
        'adjustment': 'none', 'source_url': 'https://old-provider.example',
        'instruments': {'510300.SH': {'symbol': '510300.SH', 'name': '沪深300ETF', 'kind': 'etf'}}}))
    before = (project/'data'/'real'/'market.csv').read_bytes()
    base = repository.list()[0]
    manager = DownloadManager(project, project/'state', provider=OtherProvider(project), repository=repository)
    try:
        dataset_id = manager._publish('alternative', {'symbol': '002015.SZ', 'start': base['start'], 'end': base['end']})
    finally:
        manager.close()
    published = project/'data'/dataset_id
    manifest = json.loads((published/'market_manifest.json').read_text())
    assert manifest['source'] == 'managed baseline + other-provider'
    assert manifest['symbol_sources']['002015.SZ']['source'] == 'other-provider'
    assert 'source_url' not in manifest
    assert 'provider-specific limitation' in manifest['warnings']
    assert manifest['instruments']['510300.SH']['name'] == '沪深300ETF'
    assert (project/'data'/'real'/'market.csv').read_bytes() == before
    assert repository.list() == workbench.datasets(project)
    result = workbench.execute(project, {'dataset_id': dataset_id, 'parameters': {'symbol': '002015.SZ'}}, project/'result')
    assert result['trades']


@pytest.mark.parametrize('fault', ['hash', 'adjustment', 'missing', 'duplicate', 'price', 'missing_hash', 'missing_source', 'missing_adjustment', 'raw_escape', 'raw_hash'])
def test_repository_rejects_invalid_provider_output_before_publish(project, fault):
    from strategy.dataset_repository import LocalDatasetRepository
    repository = LocalDatasetRepository(project)
    prepared = repository.prepare('invalid')
    base = repository.list()[0]
    request = {'symbol': '002015.SZ', 'start': base['start'], 'end': base['end']}
    provider = OtherProvider(project)
    provider.download(request['start'], request['end'], prepared.stage/'download', [request['symbol']], prepared.adjustment)
    path = prepared.stage/'download'/'market_manifest.json'
    manifest = json.loads(path.read_text())
    if fault == 'hash':
        manifest['market_sha256'] = 'corrupt'
    elif fault == 'adjustment':
        manifest['adjustment'] = 'qfq'
    elif fault.startswith('missing_'):
        manifest.pop({'missing_hash':'market_sha256', 'missing_source':'source', 'missing_adjustment':'adjustment'}[fault])
    elif fault.startswith('raw_'):
        raw = prepared.stage/'download'/'raw'
        raw.mkdir()
        (raw/'response.json').write_text('{}')
        manifest['raw_dir'] = str(raw if fault == 'raw_hash' else raw/'..'/'..')
        manifest['raw_sha256'] = {'response.json': 'wrong'}
    else:
        csv = prepared.stage/'download'/'market.csv'
        rows = pd.read_csv(csv)
        if fault == 'missing':
            rows = rows.iloc[1:]
        elif fault == 'duplicate':
            rows = pd.concat([rows, rows.iloc[:1]])
        else:
            rows.loc[0, 'open'] = -1
        rows.to_csv(csv, index=False)
        # 内容哈希正确时，也必须由仓库拒绝不合法的行情语义。
        manifest['market_sha256'] = hashlib.sha256(csv.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        repository.publish(prepared, request, provider.resolve(request['symbol']))
    assert not list((project/'data').glob('managed_*'))


@pytest.mark.parametrize('symlink', [False, True])
def test_declared_raw_evidence_survives_atomic_publish(project, symlink):
    from strategy.dataset_repository import LocalDatasetRepository
    repository = LocalDatasetRepository(project)
    prepared = repository.prepare('raw_ok')
    base = repository.list()[0]
    request = {'symbol':'002015.SZ', 'start':base['start'], 'end':base['end']}
    provider = OtherProvider(project)
    output = prepared.stage/'download'
    provider.download(request['start'], request['end'], output, ['002015.SZ'], prepared.adjustment)
    raw = output/'raw'
    raw.mkdir()
    (raw/'response.json').write_text('{}')
    if symlink:
        (raw/'absolute-link.json').symlink_to(raw/'response.json')
    manifest = json.loads((output/'market_manifest.json').read_text())
    manifest.update(raw_dir=str(raw), raw_sha256={'response.json': hashlib.sha256(b'{}').hexdigest()})
    (output/'market_manifest.json').write_text(json.dumps(manifest))
    if symlink:
        with pytest.raises(ValueError, match='符号链接'):
            repository.publish(prepared, request, provider.resolve('002015.SZ'))
        assert not list((project/'data').glob('managed_*'))
        return
    identifier = repository.publish(prepared, request, provider.resolve('002015.SZ'))
    published = project/'data'/identifier
    result = json.loads((published/'market_manifest.json').read_text())
    assert (published/result['download']['raw_dir']/'response.json').read_text() == '{}'
