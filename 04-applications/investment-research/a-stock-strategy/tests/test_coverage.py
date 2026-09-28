import hashlib
import json
import pandas as pd
import pytest
from strategy.market_data.coverage import CoverageIndex, segments


def source(root, name, dates, price=10, universe='SH_SZ_BJ', empty=()):
    folder=root/'data'/name
    folder.mkdir(parents=True)
    pd.DataFrame([dict(date=d,symbol='000001.SH',open=price,high=price,low=price,close=price,volume=1,amount=1,is_suspended=False,limit_up=False,limit_down=False) for d in dates]).to_csv(folder/'market.csv',index=False)
    pd.DataFrame([dict(date=d,declining_count=5,total_count=10,source='tushare.daily') for d in dates]).to_csv(folder/'breadth.csv',index=False)
    for name,file,field,extra in [('market_manifest.json','market.csv','market_sha256',{'adjustment':'qfq'}),('manifest.json','breadth.csv','breadth_sha256',{'universe':universe,'empty_dates':list(empty),'start':min([*dates,*empty]),'end':max([*dates,*empty])})]:
        (folder/name).write_text(json.dumps(dict(source='tushare.daily',**extra,**{field:hashlib.sha256((folder/file).read_bytes()).hexdigest()})))
    return folder


def test_union_gap_plan_snapshot_and_cache(tmp_path, monkeypatch):
    source(tmp_path,'real',['2026-01-05','2026-01-06'])
    source(tmp_path,'foundation_a',['2026-01-08','2026-01-09'])
    coverage=CoverageIndex(tmp_path)
    assert len(coverage.summary()['common'])==2
    assert coverage.plan('2026-01-05','2026-01-09')['index_missing']==[dict(start='2026-01-07',end='2026-01-07',days=1)]
    with pytest.raises(Exception): coverage.snapshot('2026-01-05','2026-01-09')
    monkeypatch.setattr(pd,'read_csv',lambda *a,**k: pytest.fail('unchanged CSV rescanned'))
    assert len(CoverageIndex(tmp_path).index)==4


def test_conflicts_and_corrupt_source_isolation(tmp_path):
    source(tmp_path,'real',['2026-01-05','2026-01-06'])
    source(tmp_path,'foundation_a',['2026-01-06','2026-01-07'],price=11)
    folder=source(tmp_path,'foundation_b',['2026-01-08'])
    (folder/'market.csv').write_text('broken')
    coverage=CoverageIndex(tmp_path)
    assert coverage.index.date.dt.strftime('%Y-%m-%d').tolist()==['2026-01-05','2026-01-07']
    assert coverage.conflicts[0]['date']=='2026-01-06'
    assert coverage.errors


def test_closure_snapshot_provenance_and_skip_derived(tmp_path):
    source(tmp_path,'real',['2026-01-05','2026-01-07'],empty=['2026-01-06'])
    coverage=CoverageIndex(tmp_path)
    assert coverage.plan('2026-01-05','2026-01-07')['index_missing']==[]
    name=coverage.snapshot('2026-01-05','2026-01-07',identifier='abc')
    assert name=='foundation_abc'
    manifest=json.loads((tmp_path/'data'/name/'manifest.json').read_text())
    assert manifest['coverage_snapshot'] and manifest['sources'][0]['hashes']
    assert len(CoverageIndex(tmp_path).sources)==1
    with pytest.raises(Exception): coverage.snapshot('2026-01-05','2026-01-07',identifier='abc')


def test_incompatible_breadth_and_contradicted_closure(tmp_path):
    source(tmp_path,'real',['2026-01-05'],empty=['2026-01-06'])
    source(tmp_path,'foundation_a',['2026-01-06'],universe='SH_SZ')
    coverage=CoverageIndex(tmp_path)
    assert '2026-01-06' not in coverage.closed_dates
    assert len(coverage.breadth)==1 and coverage.errors


def test_segments_do_not_compress_weekday_gaps():
    assert len(segments(['2026-01-05','2026-01-07']))==2
    assert segments(['2026-01-09','2026-01-12'])==[dict(start='2026-01-09',end='2026-01-12',days=2)]


def test_partial_components_reusable_snapshot_and_volume_units(tmp_path):
    first=source(tmp_path,'real',['2026-01-05','2026-01-06'])
    extra=source(tmp_path,'parts',['2026-01-07','2026-01-08'])
    coverage=CoverageIndex(tmp_path,extra_folders=[extra])
    published=coverage.snapshot('2026-01-05','2026-01-08',reusable=True)
    assert len(CoverageIndex(tmp_path).index)==4
    assert len(CoverageIndex(tmp_path).sources)==2
    (extra/'market.csv').unlink(); (extra/'market_manifest.json').unlink()
    assert len(CoverageIndex(tmp_path,extra_folders=[extra]).breadth)==4
    frame=pd.read_csv(first/'market.csv'); frame['volume']=100
    frame.to_csv(first/'market.csv',index=False)
    manifest=json.loads((first/'market_manifest.json').read_text())
    manifest['market_sha256']=hashlib.sha256((first/'market.csv').read_bytes()).hexdigest()
    (first/'market_manifest.json').write_text(json.dumps(manifest))
    assert not CoverageIndex(tmp_path).conflicts


def test_breadth_conflict_excluded_but_index_retained(tmp_path):
    source(tmp_path,'real',['2026-01-05','2026-01-06'])
    folder=source(tmp_path,'foundation_a',['2026-01-06'])
    frame=pd.read_csv(folder/'breadth.csv'); frame['declining_count']=6
    frame.to_csv(folder/'breadth.csv',index=False)
    manifest=json.loads((folder/'manifest.json').read_text())
    manifest['breadth_sha256']=hashlib.sha256((folder/'breadth.csv').read_bytes()).hexdigest()
    (folder/'manifest.json').write_text(json.dumps(manifest))
    coverage=CoverageIndex(tmp_path)
    assert len(coverage.index)==2 and len(coverage.breadth)==1
    assert coverage.conflicts[0]['kind']=='breadth'


def test_holiday_only_component_and_snapshot_warnings(tmp_path):
    source(tmp_path,'real',['2026-01-05','2026-01-07'])
    folder=tmp_path/'holiday'; folder.mkdir()
    pd.DataFrame(columns=['date','declining_count','total_count','source']).to_csv(folder/'breadth.csv',index=False)
    raw=folder/'raw'; raw.mkdir()
    (raw/'2026-01-06.csv').write_text('trade_date,ts_code,pct_chg\n')
    manifest=dict(source='tushare.daily',universe='SH_SZ_BJ',start='2026-01-06',end='2026-01-06',empty_dates=['2026-01-06'],raw_dir=str(raw),raw_sha256={'2026-01-06':hashlib.sha256((raw/'2026-01-06.csv').read_bytes()).hexdigest()},breadth_sha256=hashlib.sha256((folder/'breadth.csv').read_bytes()).hexdigest())
    (folder/'manifest.json').write_text(json.dumps(manifest))
    coverage=CoverageIndex(tmp_path,extra_folders=[folder])
    assert coverage.closed_dates=={'2026-01-06'}
    name=coverage.snapshot('2026-01-05','2026-01-07')
    saved=json.loads((tmp_path/'data'/name/'manifest.json').read_text())
    assert saved['complete_universe_verified'] is False
    assert saved['warnings'] and saved['calendar_status']
    assert any('raw_sha256' in item.get('manifests',{}).get('manifest.json',{}) for item in saved['sources'])
    (raw/'2026-01-06.csv').write_text('tampered')
    assert not CoverageIndex(tmp_path,extra_folders=[folder]).closed_dates


@pytest.mark.parametrize('empty',['2026-01-10','2026-01-08','2026-01-06T12:00:00'])
def test_invalid_closure_never_fills_gap(tmp_path,empty):
    folder=source(tmp_path,'real',['2026-01-05','2026-01-07'])
    manifest=json.loads((folder/'manifest.json').read_text()); manifest['empty_dates']=[empty]
    (folder/'manifest.json').write_text(json.dumps(manifest))
    coverage=CoverageIndex(tmp_path)
    assert not coverage.closed_dates
    assert coverage.errors


def test_legacy_real_missing_hash_is_validated_and_warned(tmp_path):
    folder=source(tmp_path,'real',['2026-01-05','2026-01-06'])
    manifest=json.loads((folder/'manifest.json').read_text()); manifest.pop('breadth_sha256')
    (folder/'manifest.json').write_text(json.dumps(manifest))
    coverage=CoverageIndex(tmp_path)
    assert len(coverage.breadth)==2
    evidence=coverage.sources[0]['manifests']['manifest.json']
    assert evidence['warnings'] and coverage.sources[0]['hashes']['breadth.csv']
    source(tmp_path,'foundation_a',['2026-01-07'])
    folder=tmp_path/'data'/'foundation_a'
    manifest=json.loads((folder/'manifest.json').read_text()); manifest.pop('breadth_sha256')
    (folder/'manifest.json').write_text(json.dumps(manifest))
    assert len(CoverageIndex(tmp_path).breadth)==2


def test_reusable_single_session_keeps_research_minimum(tmp_path):
    source(tmp_path,'real',['2026-01-05'])
    coverage=CoverageIndex(tmp_path)
    with pytest.raises(Exception): coverage.snapshot('2026-01-05','2026-01-05')
    coverage.snapshot('2026-01-05','2026-01-05',reusable=True)
    assert len(CoverageIndex(tmp_path).index)==1


def test_reusable_holiday_only_preserves_schema_and_closures(tmp_path):
    folder=tmp_path/'parts'; folder.mkdir()
    pd.DataFrame(columns=['date','declining_count','total_count','source']).to_csv(folder/'breadth.csv',index=False)
    manifest=dict(source='tushare.daily',universe='SH_SZ_BJ',start='2026-01-06',end='2026-01-06',empty_dates=['2026-01-06'],breadth_sha256=hashlib.sha256((folder/'breadth.csv').read_bytes()).hexdigest())
    (folder/'manifest.json').write_text(json.dumps(manifest))
    coverage=CoverageIndex(tmp_path,extra_folders=[folder])
    with pytest.raises(Exception): coverage.snapshot('2026-01-06','2026-01-06')
    coverage.snapshot('2026-01-06','2026-01-06',reusable=True)
    restored=CoverageIndex(tmp_path)
    assert restored.closed_dates=={'2026-01-06'} and not restored.errors
    assert restored.plan('2026-01-06','2026-01-06')['index_missing']==[]
    assert 'open' in restored.index and 'source' in restored.breadth
