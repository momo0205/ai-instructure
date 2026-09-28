from pathlib import Path
import json,hashlib
import pandas as pd
from test_foundation_planning import seed,write_part
from strategy.application.data_management import DataManagementService


def setup(root):
    seed(root,['2026-01-05','2026-01-06'])
    for kind in ('index','breadth'):write_part(root/'data/foundation_abcd',['2026-01-07','2026-01-08','2026-01-09'],kind)
    frame=pd.concat([pd.read_csv(root/'data/real/market.csv'),pd.read_csv(root/'data/foundation_abcd/market.csv')])
    frame.symbol='600519.SH'
    folder=root/'data/asset_test';folder.mkdir()
    frame.to_csv(folder/'market.csv',index=False)
    manifest=dict(source='test',adjustment='qfq',market_sha256=hashlib.sha256((folder/'market.csv').read_bytes()).hexdigest(),updated_symbol='600519.SH',instruments={'600519.SH':{'symbol':'600519.SH','kind':'stock','name':'贵州茅台'}},start='2026-01-05',end='2026-01-09',requested_start='2026-01-05',requested_end='2026-01-09',created_at='2026-09-23',warnings=[])
    (folder/'market_manifest.json').write_text(json.dumps(manifest))


def test_asset_research_uses_union_of_foundations(tmp_path):
    setup(tmp_path)
    service=DataManagementService(tmp_path)
    asset=service.detail('asset_test')
    assert asset['coverage']['research']==[dict(start='2026-01-05',end='2026-01-09',days=5)]
    result=service.prepare_research('asset_test')
    assert (result['start'],result['end'])==('2026-01-05','2026-01-09')
    assert len(pd.read_csv(tmp_path/'data'/result['dataset_id']/'breadth.csv'))==5


def test_selected_interval_is_revalidated(tmp_path):
    import pytest
    setup(tmp_path)
    service=DataManagementService(tmp_path)
    with pytest.raises(ValueError):service.prepare_research('asset_test',start='2026-01-01',end='2026-01-09')
    result=service.prepare_research('asset_test',start='2026-01-06',end='2026-01-08')
    assert result['start']=='2026-01-06' and result['end']=='2026-01-08'


def test_legacy_timeline_prepares_cumulative_snapshot_before_running(tmp_path):
    import shutil
    from strategy.application.requests import validate_request
    setup(tmp_path)
    folder=tmp_path/'data/managed_cdef';shutil.copytree(tmp_path/'data/asset_test',folder)
    stock=pd.read_csv(folder/'market.csv')
    index=pd.concat([pd.read_csv(tmp_path/'data/real/market.csv'),pd.read_csv(tmp_path/'data/foundation_abcd/market.csv')])
    pd.concat([stock,index]).sort_values(['date','symbol']).to_csv(folder/'market.csv',index=False)
    path=folder/'market_manifest.json';manifest=json.loads(path.read_text());manifest['market_sha256']=hashlib.sha256((folder/'market.csv').read_bytes()).hexdigest();path.write_text(json.dumps(manifest))
    shutil.copyfile(tmp_path/'data/real/breadth.csv',folder/'breadth.csv')
    shutil.copyfile(tmp_path/'data/real/manifest.json',folder/'manifest.json')
    service=DataManagementService(tmp_path)
    result=service.prepare_legacy('managed_cdef','600519.SH',start='2026-01-05',end='2026-01-09')
    assert result['dataset_id']!='managed_cdef'
    validate_request(tmp_path,dict(dataset_id=result['dataset_id'],parameters={'symbol':'600519.SH'},start=result['start'],end=result['end']))
    assert len(pd.read_csv(folder/'breadth.csv'))==2
