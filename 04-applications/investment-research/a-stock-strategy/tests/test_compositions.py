import hashlib
import json
from pathlib import Path
import shutil
import pandas as pd
import pytest
from strategy.application.compositions import CompositionService
from strategy.market_data.repository import datasets

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def project(tmp_path):
    for name,symbol in [('real','588000.SH'),('managed_a','510300.SH'),('managed_b','159915.SZ')]:
        folder=tmp_path/'data'/name;folder.mkdir(parents=True)
        frame=pd.read_csv(ROOT/'data/mvp_sample/market.csv')
        frame=frame[frame.symbol.isin(['000001.SH',symbol])]
        frame.to_csv(folder/'market.csv',index=False)
        shutil.copyfile(ROOT/'data/mvp_sample/breadth.csv',folder/'breadth.csv')
        # Fixture only: catalog is made real for tests, never published as actual market data.
        (folder/'market_manifest.json').write_text(json.dumps({'source':'test-fixture','adjustment':'qfq'}))
    return tmp_path


def request():return {'base_dataset_id':'real','members':[{'dataset_id':'managed_a','symbol':'510300.SH'},{'dataset_id':'managed_b','symbol':'159915.SZ'}]}


def test_preview_publish_and_inputs_unchanged(project):
    service=CompositionService(project)
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (project/'data').rglob('*') if p.is_file()}
    preview=service.preview(request());assert preview['sessions']>2
    assert len(datasets(project))==3
    result=service.create(request()|{'preview_digest':preview['preview_digest']})
    item=next(d for d in datasets(project) if d['id']==result['dataset_id'])
    assert set(item['symbols'])=={'000001.SH','510300.SH','159915.SZ'}
    assert '组合研究数据集' in item['name']
    for p,digest in before.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest
    manifest=json.loads((project/'data'/item['id']/'market_manifest.json').read_text())
    assert len(manifest['composition']['members'])==2

@pytest.mark.parametrize('change',['duplicate','adjustment','gap','index','breadth','stale'])
def test_rejects_conflicts(project,change):
    service=CompositionService(project);payload=request();preview=service.preview(payload)
    folder=project/'data/managed_b'
    if change=='duplicate':payload['members'][1]=payload['members'][0]
    elif change=='adjustment':(folder/'market_manifest.json').write_text(json.dumps({'adjustment':'none'}))
    elif change=='breadth':
        frame=pd.read_csv(folder/'breadth.csv');frame.loc[3,'declining_count']+=1;frame.to_csv(folder/'breadth.csv',index=False)
    elif change in ('gap','index'):
        frame=pd.read_csv(folder/'market.csv')
        if change=='gap':frame=frame.drop(frame[frame.symbol=='159915.SZ'].index[3])
        else:
            frame.loc[frame.symbol=='000001.SH',['open','high','low','close']]*=2
        frame.to_csv(folder/'market.csv',index=False)
    else:
        manifest=json.loads((folder/'market_manifest.json').read_text());manifest['warnings']=['new warning'];(folder/'market_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):service.create(payload|{'preview_digest':preview['preview_digest']})
    assert len(list((project/'data').glob('managed_*')))==2

def test_common_range_is_trimmed_and_http_contract(project):
    from strategy.interfaces.web.server import dispatch
    folder=project/'data/managed_b'
    frame=pd.read_csv(folder/'market.csv');dates=sorted(frame.date.unique())
    frame=frame[(frame.symbol=='000001.SH')|frame.date.between(dates[5],dates[-6])]
    frame.to_csv(folder/'market.csv',index=False)
    status,preview=dispatch('POST','/api/compositions/preview',request(),project,None)
    assert status==200 and preview['start']==dates[5] and preview['end']==dates[-6]
    status,result=dispatch('POST','/api/compositions',request()|{'preview_digest':preview['preview_digest']},project,None)
    assert status==201 and result['dataset_id'].startswith('managed_')
    for symbol,rows in pd.read_csv(project/'data'/result['dataset_id']/'market.csv').groupby('symbol'):
        assert rows.date.min()==dates[5] and rows.date.max()==dates[-6]


def test_unknown_and_sample_sources_rejected(project):
    service=CompositionService(project)
    for identifier in ('../real','missing','mvp_sample'):
        with pytest.raises(ValueError):service.preview(request()|{'base_dataset_id':identifier})
    with pytest.raises(ValueError):service.create(request())

def test_equal_index_values_allow_csv_numeric_dtype_difference(project):
    folder=project/'data/managed_b';frame=pd.read_csv(folder/'market.csv')
    frame['volume']=frame.volume.astype(float);frame.to_csv(folder/'market.csv',index=False)
    service=CompositionService(project);preview=service.preview(request())
    result=service.create(request()|{'preview_digest':preview['preview_digest']})
    manifest=json.loads((project/'data'/result['dataset_id']/'market_manifest.json').read_text())
    source=manifest['symbol_sources']['159915.SZ']
    assert source['original_dataset_root']==str(folder.resolve())
    assert source['raw_evidence']=='external_to_composition'
