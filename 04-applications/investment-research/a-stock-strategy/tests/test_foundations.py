import hashlib
import json
from pathlib import Path
import pandas as pd
import pytest
from test_data_management import make_project
from strategy.application.data_management import DataManagementService


def providers(tmp_path, missing=False, truncate=False):
    asset=make_project(tmp_path,shift=True)
    frame=pd.read_csv(asset/'market.csv')
    old=frame.date.unique(); dates=pd.bdate_range('2026-01-05',periods=len(old)).strftime('%Y-%m-%d').tolist()
    frame.date=frame.date.map(dict(zip(old,dates))); frame.to_csv(asset/'market.csv',index=False)
    manifest=json.loads((asset/'market_manifest.json').read_text());manifest.update(start=dates[0],end=dates[-1],market_sha256=hashlib.sha256((asset/'market.csv').read_bytes()).hexdigest());(asset/'market_manifest.json').write_text(json.dumps(manifest))
    def market(start,end,output_dir,**kwargs):
        out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
        frame=pd.read_csv(asset/'market.csv'); frame=frame[frame.symbol=='000001.SH']
        if truncate: frame=frame.iloc[1:]
        frame.to_csv(out/'market.csv',index=False)
        raw=out/'raw';raw.mkdir();(raw/'response.json').write_text('{}')
        (out/'market_manifest.json').write_text(json.dumps(dict(source='test',adjustment='qfq',market_sha256=hashlib.sha256((out/'market.csv').read_bytes()).hexdigest(),raw_dir=str(raw.resolve()),raw_sha256={'response.json':hashlib.sha256(b'{}').hexdigest()})))
    def breadth(start,end,output_dir,**kwargs):
        out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
        frame=pd.read_csv(tmp_path/'data/real/breadth.csv');frame.date=dates
        if missing or truncate:frame=frame.iloc[1:]
        frame.to_csv(out/'breadth.csv',index=False)
        raw=out/'raw';raw.mkdir()
        hashes={}
        for date in dates:
            (raw/f'{date}.csv').write_text('trade_date,ts_code,pct_chg\n')
            hashes[date]=hashlib.sha256((raw/f'{date}.csv').read_bytes()).hexdigest()
        (out/'manifest.json').write_text(json.dumps(dict(source='test',start=start,end=end,coverage_dates=frame.date.tolist(),empty_dates=[],breadth_sha256=hashlib.sha256((out/'breadth.csv').read_bytes()).hexdigest(),raw_dir=str(raw.resolve()),raw_sha256=hashes)))
    return dates,market,breadth


def test_publish_recent_foundation_and_prepare_without_mutation(tmp_path):
    from strategy.market_data.foundations import update_foundation
    dates,market,breadth=providers(tmp_path)
    originals={p:p.read_bytes() for p in (tmp_path/'data').rglob('*') if p.is_file()}
    identifier=update_foundation(tmp_path,'abc123',dates[0],dates[-1],market_downloader=market,breadth_downloader=breadth)
    assert identifier=='foundation_abc123'
    for p,data in originals.items(): assert p.read_bytes()==data
    service=DataManagementService(tmp_path)
    ready=service.detail('asset_example')['readiness']
    assert ready['foundation_id']==identifier and ready['status']=='ready'
    result=service.prepare_research('asset_example')
    manifest=json.loads((tmp_path/'data'/result['dataset_id']/'market_manifest.json').read_text())
    assert manifest['parent_dataset']==identifier
    for name in ('market_manifest.json','manifest.json'):
        manifest=json.loads((tmp_path/'data'/identifier/name).read_text())
        assert not Path(manifest['raw_dir']).is_absolute()
        assert (tmp_path/'data'/identifier/manifest['raw_dir']).is_dir()


@pytest.mark.parametrize('missing,truncate',[(True,False),(False,True)])
def test_incomplete_foundation_is_not_published(tmp_path,missing,truncate):
    from strategy.market_data.foundations import update_foundation
    dates,market,breadth=providers(tmp_path,missing,truncate)
    with pytest.raises(ValueError):update_foundation(tmp_path,'abc123',dates[0],dates[-1],market_downloader=market,breadth_downloader=breadth)
    assert not (tmp_path/'data/foundation_abc123').exists()
    assert not list((tmp_path/'data').glob('.foundation_*'))


def test_corrupt_foundation_does_not_hide_healthy_real(tmp_path):
    make_project(tmp_path)
    folder=tmp_path/'data/foundation_bad';folder.mkdir();(folder/'market_manifest.json').write_text('{')
    catalog=DataManagementService(tmp_path).catalog()
    assert len(catalog['foundations'])==2
    assert catalog['assets'][0]['readiness']['foundation_id']=='real'
    assert catalog['errors']


def test_healthy_foundation_survives_corrupt_real(tmp_path):
    from strategy.market_data.foundations import update_foundation
    dates,market,breadth=providers(tmp_path)
    update_foundation(tmp_path,'abcd',dates[0],dates[-1],market_downloader=market,breadth_downloader=breadth)
    (tmp_path/'data/real/market_manifest.json').write_text('{')
    catalog=DataManagementService(tmp_path).catalog()
    assert catalog['assets'][0]['readiness']['foundation_id']=='foundation_abcd'
    assert catalog['errors']


@pytest.mark.parametrize('identifier',['../x','real','../../real','UPPER',''])
def test_unsafe_identifiers_rejected(tmp_path,identifier):
    from strategy.market_data.foundations import update_foundation
    from strategy.market_data.repository import LocalDatasetRepository
    with pytest.raises(ValueError):update_foundation(tmp_path,identifier,'2026-01-05','2026-01-06')
    if identifier!='real':
        with pytest.raises(ValueError):LocalDatasetRepository(tmp_path,baseline_id=identifier)


def test_published_nested_manifests_retain_valid_relative_evidence(tmp_path):
    from strategy.market_data.foundations import update_foundation
    dates,market,breadth=providers(tmp_path)
    identifier=update_foundation(tmp_path,'abc',dates[0],dates[-1],market_downloader=market,breadth_downloader=breadth)
    folder=tmp_path/'data'/identifier
    for name in ['index/market_manifest.json','breadth/manifest.json']:
        manifest=json.loads((folder/name).read_text())
        assert manifest['raw_dir_base']=='dataset_root'
        assert (folder/manifest['raw_dir']).is_dir()


def test_boundary_holiday_requires_retained_empty_response(tmp_path):
    from strategy.market_data.foundations import update_foundation
    dates,market,breadth=providers(tmp_path)
    def with_holiday(start,end,output_dir,**kwargs):
        breadth(start,end,output_dir,**kwargs)
        out=Path(output_dir);path=out/'manifest.json';manifest=json.loads(path.read_text())
        holiday='2026-01-02'
        (out/'raw'/f'{holiday}.csv').write_text('trade_date,ts_code,pct_chg\n')
        manifest['empty_dates']=[holiday]
        manifest['raw_sha256'][holiday]=hashlib.sha256((out/'raw'/f'{holiday}.csv').read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))
    assert update_foundation(tmp_path,'fed','2026-01-02',dates[-1],market_downloader=market,breadth_downloader=with_holiday)=='foundation_fed'


def test_raw_tamper_rejects_publish(tmp_path):
    from strategy.market_data.foundations import update_foundation
    dates,market,breadth=providers(tmp_path)
    def corrupt(start,end,output_dir,**kwargs):
        market(start,end,output_dir,**kwargs)
        (Path(output_dir)/'raw/response.json').write_text('tampered')
    with pytest.raises(ValueError,match='哈希'):
        update_foundation(tmp_path,'fed',dates[0],dates[-1],market_downloader=corrupt,breadth_downloader=breadth)
    assert not (tmp_path/'data/foundation_fed').exists()


def test_malformed_foundation_manifest_is_isolated(tmp_path):
    make_project(tmp_path)
    folder=tmp_path/'data/foundation_bad';folder.mkdir();(folder/'market_manifest.json').write_text('[]')
    catalog=DataManagementService(tmp_path).catalog()
    assert catalog['assets'][0]['readiness']['foundation_id']=='real'
    assert catalog['errors']


def test_prepared_research_retains_breadth_evidence_reference(tmp_path):
    from strategy.market_data.foundations import update_foundation
    dates,market,breadth=providers(tmp_path)
    foundation=update_foundation(tmp_path,'aabb',dates[0],dates[-1],market_downloader=market,breadth_downloader=breadth)
    result=DataManagementService(tmp_path).prepare_research('asset_example')
    manifest=json.loads((tmp_path/'data'/result['dataset_id']/'manifest.json').read_text())
    assert manifest['raw_dir_base']=='absolute'
    assert Path(manifest['raw_dir']).is_dir()
    assert Path(manifest['raw_dir']).is_relative_to(tmp_path/'data'/foundation)


def test_foundation_missing_manifest_cannot_be_used(tmp_path):
    from strategy.market_data.foundations import update_foundation
    dates,market,breadth=providers(tmp_path)
    foundation=update_foundation(tmp_path,'aabb',dates[0],dates[-1],market_downloader=market,breadth_downloader=breadth)
    (tmp_path/'data'/foundation/'manifest.json').unlink()
    assert DataManagementService(tmp_path).detail('asset_example')['readiness']['status']=='blocked'
