"""Independent assets preserve evidence without pretending missing sessions are tradable."""
import hashlib
import json
import pandas as pd
import pytest

from strategy.market_data import assets

REQUEST = dict(symbol='600519.SH', start='2026-01-01', end='2026-01-05')
META = dict(symbol='600519.SH', name='贵州茅台', kind='stock')


def staged(root, identifier='test', index=True):
    repo = assets.AssetRepository(root)
    prepared = repo.prepare(identifier)
    folder = prepared.stage/'download'
    dates = [('600519.SH','2026-01-02'), ('600519.SH','2026-01-05')]
    if index:
        dates += [('000001.SH','2026-01-02'), ('000001.SH','2026-01-05')]
    pd.DataFrame([dict(date=d, symbol=s, open=10, high=11, low=9, close=10,
                      volume=100, amount=1000, is_suspended=False, limit_up=False, limit_down=False)
                  for s,d in dates]).sort_values(['date','symbol']).to_csv(folder/'market.csv',index=False)
    raw = folder/'raw'; raw.mkdir(); (raw/'response.json').write_text('{}')
    manifest = dict(source='fixture',adjustment='qfq',market_sha256=hashlib.sha256((folder/'market.csv').read_bytes()).hexdigest(),
                    raw_dir=str(raw),raw_sha256={'response.json':hashlib.sha256(b'{}').hexdigest()})
    (folder/'market_manifest.json').write_text(json.dumps(manifest))
    return repo, prepared


def test_publish_without_baseline_preserves_actual_requested_and_raw(tmp_path):
    repo,p = staged(tmp_path)
    identifier = repo.publish(p,REQUEST,META)
    row = assets.list_assets(tmp_path)[0]
    assert identifier == row['id'] == 'asset_test'
    assert row['requested_start'] == '2026-01-01'
    assert row['start'] == '2026-01-02'
    assert row['rows'] == 2
    assert row['quality']['coverage_status'] == 'matches_observed_index'
    detail = assets.detail_asset(tmp_path,identifier)
    assert [x['date'] for x in detail['preview']] == ['2026-01-02','2026-01-05']
    manifest = json.loads((tmp_path/'data'/identifier/'market_manifest.json').read_text())
    assert (tmp_path/'data'/identifier/manifest['raw_dir']/'response.json').is_file()


def test_stock_only_is_saved_with_unverified_calendar(tmp_path):
    repo,p = staged(tmp_path,index=False)
    identifier = repo.publish(p,REQUEST,META)
    assert assets.detail_asset(tmp_path,identifier)['quality']['coverage_status'] == 'calendar_unverified'


def test_gap_saved_and_not_reported_as_suspension(tmp_path):
    repo,p = staged(tmp_path)
    path=p.stage/'download'/'market.csv'; frame=pd.read_csv(path)
    frame=frame[~((frame.symbol=='600519.SH') & (frame.date=='2026-01-05'))]; frame.to_csv(path,index=False)
    mp=path.parent/'market_manifest.json'; m=json.loads(mp.read_text());m['market_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();mp.write_text(json.dumps(m))
    identifier=repo.publish(p,REQUEST,META)
    quality=assets.detail_asset(tmp_path,identifier)['quality']
    assert quality['missing_dates'] == ['2026-01-05']
    assert quality['coverage_status'] == 'gaps_detected'


@pytest.mark.parametrize('damage',['hash','raw','symlink','identity','dates'])
def test_invalid_evidence_rejected(tmp_path,damage):
    repo,p=staged(tmp_path)
    folder=p.stage/'download'; request=dict(REQUEST); meta=dict(META)
    if damage=='hash': (folder/'market.csv').write_text('broken')
    if damage=='raw': (folder/'raw'/'response.json').write_text('changed')
    if damage=='symlink':
        path=folder/'raw'/'response.json'; path.unlink(); path.symlink_to('/etc/hosts')
    if damage=='identity': meta['symbol']='002015.SZ'
    if damage=='dates': request['end']='2026-01-03'
    with pytest.raises(ValueError): repo.publish(p,request,meta)
    assert not (tmp_path/'data'/'asset_test').exists()


@pytest.mark.parametrize('identifier',['../real','asset_../real','/tmp/no'])
def test_identifier_cannot_escape_root(tmp_path,identifier):
    with pytest.raises(ValueError): assets.AssetRepository(tmp_path).prepare(identifier)
    with pytest.raises(ValueError): assets.detail_asset(tmp_path,identifier)


def test_independent_tencent_keeps_partial_years_and_calendar_mismatch(tmp_path):
    from strategy.market_data.tencent import download_market
    def fetch(params):
        symbol,_,start,*_=params['param'].split(',')
        rows=[] if start.startswith('2024') else [['2025-01-02','10','10','11','9','100',{},'3','11']]
        if symbol=='sh000001' and rows:
            rows=rows+[['2025-01-03','10','10','11','9','100',{},'3','11']]
        return {'data':{symbol:{'day' if symbol=='sh000001' else 'qfqday':rows}}}
    download_market('2024-01-01','2025-01-03',tmp_path,symbols=['600519.SH'],adjustment='qfq',requester=fetch,strict_calendar=False)
    assert len(list((tmp_path/'market_raw').rglob('*.json'))) == 4
    frame=pd.read_csv(tmp_path/'market.csv')
    assert len(frame[frame.symbol=='600519.SH'])==1
    with pytest.raises(ValueError,match='empty requested'):
        download_market('2024-01-01','2025-01-03',tmp_path/'strict',symbols=['600519.SH'],adjustment='qfq',requester=fetch)


def test_independent_provider_opts_in_without_changing_legacy_contract(monkeypatch,tmp_path):
    from strategy.market_data.provider import TencentMarketDataProvider
    seen={}
    def download(*args,**kwargs): seen.update(kwargs)
    monkeypatch.setattr('strategy.market_data.provider.download_market',download)
    TencentMarketDataProvider(independent=True).download('2024-01-01','2025-01-01',tmp_path)
    assert seen['strict_calendar'] is False


@pytest.mark.parametrize('start,end',[('2026-01-05','2026-01-01'),('2999-01-01','2999-01-02')])
def test_publication_validates_dates(tmp_path,start,end):
    repo,p=staged(tmp_path)
    with pytest.raises(ValueError): repo.publish(p,dict(REQUEST,start=start,end=end),META)


def test_published_version_cannot_be_overwritten_and_cache_detects_changes(tmp_path):
    repo,p=staged(tmp_path); identifier=repo.publish(p,REQUEST,META)
    assets.detail_asset(tmp_path,identifier)
    with pytest.raises(ValueError): repo.prepare('test')
    (tmp_path/'data'/identifier/'market.csv').write_text('changed')
    with pytest.raises(ValueError): assets.detail_asset(tmp_path,identifier)


def test_raw_parent_symlink_rejected_even_with_internal_target(tmp_path):
    repo,p=staged(tmp_path); download=p.stage/'download'
    (download/'alias').symlink_to(download/'raw',target_is_directory=True)
    mp=download/'market_manifest.json'; manifest=json.loads(mp.read_text());manifest['raw_dir']=str(download/'alias');mp.write_text(json.dumps(manifest))
    with pytest.raises(ValueError): repo.publish(p,REQUEST,META)
