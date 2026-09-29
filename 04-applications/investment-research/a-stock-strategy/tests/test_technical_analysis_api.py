"""The local HTTP boundary exposes only catalog and verified analysis inputs."""
import json

from test_technical_analysis import asset, request


def test_catalog_and_sources_are_available_without_market_breadth(tmp_path):
    from strategy.interfaces.web.server import dispatch
    asset(tmp_path, with_index=False)
    status, entries = dispatch('GET','/api/indicators',None,tmp_path,None)
    assert status == 200
    assert any(item['id'] == 'bollinger' and item['category'] == 'volatility' for item in entries)
    status, sources = dispatch('GET','/api/technical-analysis/sources',None,tmp_path,None)
    assert status == 200
    assert sources['sources'][0]['id'] == 'asset_example'


def test_broken_asset_does_not_hide_healthy_sources_or_catalog(tmp_path):
    from strategy.interfaces.web.server import dispatch
    asset(tmp_path)
    broken = tmp_path/'data'/'asset_broken'
    broken.mkdir()
    (broken/'market.csv').write_text('invalid')
    (broken/'market_manifest.json').write_text('{}')
    status, body = dispatch('GET','/api/technical-analysis/sources',None,tmp_path,None)
    assert status == 200
    assert [row['id'] for row in body['sources']] == ['asset_example']
    assert len(body['warnings']) == 1 and 'asset_broken' in body['warnings'][0]
    assert dispatch('GET','/api/indicators',None,tmp_path,None)[0] == 200


def test_analysis_endpoint_returns_strict_json_and_validation_diagnostic(tmp_path):
    from strategy.interfaces.web.server import dispatch
    asset(tmp_path, with_index=False)
    status, body = dispatch('POST','/api/technical-analysis',request(),tmp_path,None)
    assert status == 200
    assert body['rows'][0]['indicators']['ema2']['values']['value'] == 1.5
    assert json.dumps(body,allow_nan=False)
    status, error = dispatch('POST','/api/technical-analysis',request(start='bad'),tmp_path,None)
    assert status == 400
    assert error['diagnostic']['code'] == 'INVALID_REQUEST'


def test_tampered_source_has_data_validation_diagnostic(tmp_path):
    from strategy.interfaces.web.server import dispatch
    folder = asset(tmp_path)
    (folder/'market.csv').write_text('changed')
    status, error = dispatch('POST','/api/technical-analysis',request(),tmp_path,None)
    assert status == 400
    assert error['diagnostic']['code'] == 'DATA_VALIDATION_FAILED'


def test_malformed_but_rehashed_manifest_has_data_validation_diagnostic(tmp_path):
    from strategy.interfaces.web.server import dispatch
    folder = asset(tmp_path)
    path = folder/'market_manifest.json'
    manifest = json.loads(path.read_text())
    manifest['instruments'] = []
    path.write_text(json.dumps(manifest))
    status, error = dispatch('POST','/api/technical-analysis',request(),tmp_path,None)
    assert status == 400
    assert error['diagnostic']['code'] == 'DATA_VALIDATION_FAILED'
