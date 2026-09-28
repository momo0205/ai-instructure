"""Repeated preparation reuses verified immutable inputs, never dates alone."""
import hashlib
import json
import pandas as pd
from test_data_management import make_project
from strategy.application.data_management import DataManagementService


def test_repeated_prepare_reuses_verified_version(tmp_path):
    make_project(tmp_path)
    first = DataManagementService(tmp_path).prepare_research('asset_example')
    folders = set((tmp_path/'data').iterdir())
    assert DataManagementService(tmp_path).prepare_research('asset_example') == first
    assert set((tmp_path/'data').iterdir()) == folders


def test_changed_source_creates_new_version(tmp_path):
    source = make_project(tmp_path)
    first = DataManagementService(tmp_path).prepare_research('asset_example')
    frame = pd.read_csv(source/'market.csv')
    frame.loc[frame.symbol=='600519.SH', 'volume'] += 1
    frame.to_csv(source/'market.csv',index=False)
    manifest = json.loads((source/'market_manifest.json').read_text())
    manifest['market_sha256'] = hashlib.sha256((source/'market.csv').read_bytes()).hexdigest()
    (source/'market_manifest.json').write_text(json.dumps(manifest))
    assert DataManagementService(tmp_path).prepare_research('asset_example') != first


def test_tampered_candidate_is_not_reused(tmp_path):
    make_project(tmp_path)
    first = DataManagementService(tmp_path).prepare_research('asset_example')
    target = tmp_path/'data'/first['dataset_id']/'market.csv'
    target.write_text(target.read_text()+'\n')
    assert DataManagementService(tmp_path).prepare_research('asset_example') != first


def cumulative_project(tmp_path):
    from test_coverage import source
    base = source(tmp_path,'real',['2026-01-05','2026-01-06','2026-01-07'])
    asset = tmp_path/'data'/'asset_example'
    asset.mkdir()
    frame = pd.read_csv(base/'market.csv')
    frame['symbol'] = '600519.SH'
    frame.to_csv(asset/'market.csv',index=False)
    manifest = dict(source='test',adjustment='qfq',updated_symbol='600519.SH',
        instruments={'600519.SH':dict(symbol='600519.SH',name='贵州茅台',kind='stock')},
        created_at='2026-01-08T00:00:00Z',warnings=[],
        market_sha256=hashlib.sha256((asset/'market.csv').read_bytes()).hexdigest())
    (asset/'market_manifest.json').write_text(json.dumps(manifest))
    return base


def test_cumulative_repeat_range_and_dependencies(tmp_path):
    base = cumulative_project(tmp_path)
    first = DataManagementService(tmp_path).prepare_research('asset_example')
    folders = set((tmp_path/'data').iterdir())
    assert DataManagementService(tmp_path).prepare_research('asset_example') == first
    assert set((tmp_path/'data').iterdir()) == folders
    assert DataManagementService(tmp_path).prepare_research('asset_example',start='2026-01-05',end='2026-01-06') != first
    breadth = pd.read_csv(base/'breadth.csv')
    breadth['declining_count'] = 6
    breadth.to_csv(base/'breadth.csv',index=False)
    manifest = json.loads((base/'manifest.json').read_text())
    manifest['breadth_sha256'] = hashlib.sha256((base/'breadth.csv').read_bytes()).hexdigest()
    (base/'manifest.json').write_text(json.dumps(manifest))
    assert DataManagementService(tmp_path).prepare_research('asset_example') != first


def test_legacy_prepare_repeat(tmp_path):
    cumulative_project(tmp_path)
    dataset = DataManagementService(tmp_path).prepare_research('asset_example')['dataset_id']
    first = DataManagementService(tmp_path).prepare_legacy(dataset,'600519.SH')
    folders = set((tmp_path/'data').iterdir())
    assert DataManagementService(tmp_path).prepare_legacy(dataset,'600519.SH') == first
    assert set((tmp_path/'data').iterdir()) == folders


def test_coverage_snapshot_reuses_and_skips_tampering(tmp_path):
    from strategy.market_data.coverage import CoverageIndex
    cumulative_project(tmp_path)
    coverage = CoverageIndex(tmp_path)
    first = coverage.snapshot('2026-01-05','2026-01-07')
    assert CoverageIndex(tmp_path).snapshot('2026-01-05','2026-01-07') == first
    target = tmp_path/'data'/first/'breadth.csv'
    target.write_text(target.read_text()+'\n')
    assert CoverageIndex(tmp_path).snapshot('2026-01-05','2026-01-07') != first


def test_catalog_isolates_invalid_nested_metadata(tmp_path):
    cumulative_project(tmp_path)
    prepared=DataManagementService(tmp_path).prepare_research('asset_example')
    valid=DataManagementService(tmp_path).prepare_research('asset_example',start='2026-01-05',end='2026-01-06')
    path=tmp_path/'data'/prepared['dataset_id']/'market_manifest.json'
    manifest=json.loads(path.read_text()); manifest['download']['asset_reference']=[]
    path.write_text(json.dumps(manifest))
    catalog=DataManagementService(tmp_path).catalog()
    assert any(row['id']=='asset_example' for row in catalog['timeline_assets'])
    assert any(row.get('dataset_id')==valid['dataset_id'] for row in catalog['timeline_assets'])
    assert catalog['errors']


def test_nonobject_reuse_candidates_are_ignored(tmp_path):
    from strategy.market_data.coverage import CoverageIndex
    cumulative_project(tmp_path)
    expected=DataManagementService(tmp_path).prepare_research('asset_example')
    for name in ('managed_000','foundation_000'):
        folder=tmp_path/'data'/name; folder.mkdir()
        (folder/'market_manifest.json').write_text('[]')
        (folder/'manifest.json').write_text('[]')
    assert DataManagementService(tmp_path).prepare_research('asset_example')==expected
    assert CoverageIndex(tmp_path).snapshot('2026-01-05','2026-01-07')!='foundation_000'


def test_semantically_changed_foundation_not_reused(tmp_path):
    from strategy.market_data.coverage import CoverageIndex
    cumulative_project(tmp_path)
    first=CoverageIndex(tmp_path).snapshot('2026-01-05','2026-01-07')
    path=tmp_path/'data'/first/'market_manifest.json'
    manifest=json.loads(path.read_text()); manifest['adjustment']='none'
    path.write_text(json.dumps(manifest))
    assert CoverageIndex(tmp_path).snapshot('2026-01-05','2026-01-07')!=first


def test_semantically_changed_managed_not_reused(tmp_path):
    cumulative_project(tmp_path)
    first=DataManagementService(tmp_path).prepare_research('asset_example')
    path=tmp_path/'data'/first['dataset_id']/'market_manifest.json'
    manifest=json.loads(path.read_text()); manifest['adjustment']='none'
    path.write_text(json.dumps(manifest))
    assert DataManagementService(tmp_path).prepare_research('asset_example')!=first
