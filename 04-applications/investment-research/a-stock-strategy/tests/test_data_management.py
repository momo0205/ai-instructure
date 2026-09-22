"""数据资产可存在于策略依赖之外；只有准备研究时要求完整共同日期。"""
import hashlib
import json
import shutil
from pathlib import Path
import pandas as pd
import pytest
from strategy.application.downloads import DownloadManager

ROOT=Path(__file__).resolve().parents[1]


def test_download_accepts_recent_dates_without_baseline(tmp_path):
    class NoNetwork:
        def resolve(self, symbol):
            raise ValueError('probe ends before network')
    manager=DownloadManager(tmp_path,tmp_path/'state',provider=NoNetwork())
    try:
        task=manager.submit(dict(symbol='600519.SH',start='2026-01-05',end='2026-01-09'))
        assert task['status']=='queued'
    finally:
        manager.close()


@pytest.mark.parametrize('start,end',[('2026-02-01','2026-01-01'),('2026-01-01','2099-01-01')])
def test_independent_download_still_rejects_invalid_range(tmp_path,start,end):
    manager=DownloadManager(tmp_path,tmp_path/'state')
    try:
        with pytest.raises(ValueError):manager.submit(dict(symbol='600519.SH',start=start,end=end))
    finally:manager.close()


def make_project(tmp_path, shift=False):
    base=tmp_path/'data'/'real'
    shutil.copytree(ROOT/'data'/'mvp_sample',base)
    (base/'market_manifest.json').write_text(json.dumps({'source':'test','adjustment':'qfq'}))
    source=pd.read_csv(base/'market.csv')
    asset=tmp_path/'data'/'asset_example';asset.mkdir()
    source=source[source.symbol.isin(['000001.SH','588000.SH'])].copy()
    source.loc[source.symbol=='588000.SH','symbol']='600519.SH'
    if shift:source['date']=(pd.to_datetime(source.date)+pd.Timedelta(days=731)).dt.strftime('%Y-%m-%d')
    source.to_csv(asset/'market.csv',index=False)
    manifest=dict(source='test',adjustment='qfq',market_sha256=hashlib.sha256((asset/'market.csv').read_bytes()).hexdigest(),
        updated_symbol='600519.SH',instruments={'600519.SH':{'symbol':'600519.SH','name':'贵州茅台','kind':'stock'}},
        requested_start=source.date.min(),requested_end=source.date.max(),start=source.date.min(),end=source.date.max(),
        created_at='2026-09-22T00:00:00+00:00',warnings=[])
    (asset/'market_manifest.json').write_text(json.dumps(manifest))
    return asset


def test_catalog_exposes_recent_asset_and_missing_breadth(tmp_path):
    from strategy.application.data_management import DataManagementService
    make_project(tmp_path,shift=True)
    catalog=DataManagementService(tmp_path).catalog()
    assert catalog['foundations'][0]['breadth_end']=='2024-05-06'
    row=catalog['assets'][0]
    assert row['readiness']['status']=='blocked'
    assert row['readiness']['reasons']
    assert row['end']>'2025-12-31'


def test_prepare_research_preserves_asset_and_base(tmp_path):
    from strategy.application.data_management import DataManagementService
    asset=make_project(tmp_path)
    original=(asset/'market.csv').read_bytes()
    base=(tmp_path/'data'/'real'/'market.csv').read_bytes()
    service=DataManagementService(tmp_path)
    result=service.prepare_research('asset_example')
    assert result['dataset_id'].startswith('managed_')
    assert (asset/'market.csv').read_bytes()==original
    assert (tmp_path/'data'/'real'/'market.csv').read_bytes()==base
    from strategy.application.requests import validate_request
    request=validate_request(tmp_path,dict(dataset_id=result['dataset_id'],parameters={'symbol':'600519.SH'},start=result['start'],end=result['end']))
    assert request['parameters']['symbol']=='600519.SH'


def test_asset_path_not_arbitrary_and_missing_dependencies_block(tmp_path):
    from strategy.application.data_management import DataManagementService
    make_project(tmp_path,shift=True)
    service=DataManagementService(tmp_path)
    with pytest.raises(ValueError):service.detail('../real')
    with pytest.raises(ValueError):service.prepare_research('asset_example')


def test_data_management_routes(tmp_path):
    from strategy.web import dispatch
    make_project(tmp_path)
    code,body=dispatch('GET','/api/data-management',None,tmp_path,None)
    assert code==200 and body['assets']
    code,body=dispatch('GET','/api/data-assets/asset_example',None,tmp_path,None)
    assert code==200 and body['preview']
