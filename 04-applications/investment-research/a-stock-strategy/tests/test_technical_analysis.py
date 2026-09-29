"""Analysis must work on an independent, verified version without breadth."""
import hashlib
import json

import pandas as pd
import pytest


def asset(root, *, with_index=True, missing_day=False, days=4):
    folder = root/'data'/'asset_example'
    folder.mkdir(parents=True)
    rows = []
    for i, day in enumerate(pd.date_range('2026-01-01', periods=days, freq='D'), 1):
        if not missing_day or i != 3:
            rows.append(dict(date=day.date().isoformat(), symbol='600519.SH', open=i, high=i+.5,
                             low=i-.5 if i > 1 else .5, close=i, volume=i-1, amount=i*10,
                             is_suspended=False, limit_up=False, limit_down=False))
        if with_index:
            rows.append(dict(date=day.date().isoformat(), symbol='000001.SH', open=10, high=11,
                             low=9, close=10, volume=100, amount=1000, is_suspended=False,
                             limit_up=False, limit_down=False))
    market = folder/'market.csv'
    pd.DataFrame(rows).sort_values(['date','symbol']).to_csv(market,index=False)
    manifest = dict(updated_symbol='600519.SH', adjustment='qfq', source='fixture',
                    market_sha256=hashlib.sha256(market.read_bytes()).hexdigest(),
                    volume_unit='股', amount_unit='元', instruments={'600519.SH':{'name':'贵州茅台'}}, warnings=[])
    (folder/'market_manifest.json').write_text(json.dumps(manifest))
    return folder


def request(**changed):
    return dict(source_id='asset_example', symbol='600519.SH', start='2026-01-02', end='2026-01-04',
                indicators=[dict(instance_id='ema2',id='ema',parameters={'window':2})]) | changed


def test_analyzes_independent_asset_and_keeps_ema_seed_before_display_start(tmp_path):
    from strategy.application.technical_analysis import TechnicalAnalysisService
    asset(tmp_path, with_index=False)
    service = TechnicalAnalysisService(tmp_path)
    result = service.analyze(request())
    assert result['source']['id'] == 'asset_example'
    assert result['source']['adjustment'] == 'qfq'
    assert result['source']['market_sha256']
    assert result['calendar']['basis'] == 'security_only'
    assert result['calculation_start'] == '2026-01-01'
    assert result['rows'][0]['date'] == '2026-01-02'
    assert result['rows'][0]['indicators']['ema2']['values']['value'] == 1.5
    assert service.analyze(request(start='2026-01-03'))['rows'][0]['indicators']['ema2']['values']['value'] == pytest.approx(2.5)


def test_observed_index_gap_breaks_window_without_filling_price(tmp_path):
    from strategy.application.technical_analysis import TechnicalAnalysisService
    asset(tmp_path, missing_day=True)
    result = TechnicalAnalysisService(tmp_path).analyze(request(indicators=[
        dict(instance_id='s',id='sma',parameters={'window':2}),
        dict(instance_id='v',id='volume_sma',parameters={'window':2}),
    ]))
    assert result['calendar']['basis'] == 'observed_index'
    gap = result['rows'][1]
    assert gap['date'] == '2026-01-03' and gap['status'] == 'missing_quote'
    assert gap['close'] is None and gap['indicators']['s']['values']['value'] is None
    assert result['rows'][2]['indicators']['s']['values']['value'] is None
    assert result['rows'][2]['indicators']['v']['values']['value'] is None


def test_suspended_quote_is_labeled_and_keeps_observed_price(tmp_path):
    from strategy.application.technical_analysis import TechnicalAnalysisService
    folder = asset(tmp_path, with_index=False)
    market = folder/'market.csv'
    frame = pd.read_csv(market)
    frame.loc[frame.date == '2026-01-02', 'is_suspended'] = True
    frame.to_csv(market,index=False)
    manifest_path = folder/'market_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['market_sha256'] = hashlib.sha256(market.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    result = TechnicalAnalysisService(tmp_path).analyze(request())
    assert result['rows'][0]['status'] == 'suspended_quote'
    assert result['rows'][0]['trading_status'] == 'suspended'
    assert result['rows'][0]['close'] == 2


def test_false_suspension_flag_keeps_trading_status_unknown(tmp_path):
    from strategy.application.technical_analysis import TechnicalAnalysisService
    asset(tmp_path, with_index=False)
    result = TechnicalAnalysisService(tmp_path).analyze(request())
    assert result['rows'][0]['status'] == 'observed_quote'
    assert result['rows'][0]['trading_status'] == 'unknown'


def test_missing_close_keeps_valid_volume_and_resets_price_indicator(tmp_path):
    from strategy.application.technical_analysis import TechnicalAnalysisService
    folder = asset(tmp_path, with_index=False)
    market = folder/'market.csv'
    frame = pd.read_csv(market)
    frame.loc[frame.date == '2026-01-03', 'close'] = None
    frame.to_csv(market,index=False)
    manifest_path = folder/'market_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['market_sha256'] = hashlib.sha256(market.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    result = TechnicalAnalysisService(tmp_path).analyze(request(indicators=[
        dict(instance_id='s',id='sma',parameters={'window':2}),
        dict(instance_id='v',id='volume_sma',parameters={'window':2}),
    ]))
    missing = result['rows'][1]
    assert missing['close'] is None and missing['volume'] == 2
    assert missing['indicators']['s']['reason'] == 'invalid_close'
    assert missing['indicators']['v']['values']['value'] == 1.5
    assert result['rows'][2]['indicators']['s']['values']['value'] is None
    assert TechnicalAnalysisService(tmp_path).sources()['sources'][0]['id'] == 'asset_example'


def test_later_prices_do_not_change_earlier_indicator_values(tmp_path):
    from strategy.application.technical_analysis import TechnicalAnalysisService
    folder = asset(tmp_path, with_index=False)
    service = TechnicalAnalysisService(tmp_path)
    before = service.analyze(request())['rows'][0]['indicators']['ema2']['values']['value']
    market = folder/'market.csv'
    frame = pd.read_csv(market)
    frame.loc[frame.date == '2026-01-04', ['open','high','low','close']] = [100,101,99,100]
    frame.to_csv(market,index=False)
    manifest_path = folder/'market_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['market_sha256'] = hashlib.sha256(market.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    after = service.analyze(request())['rows'][0]['indicators']['ema2']['values']['value']
    assert before == after == 1.5


@pytest.mark.parametrize('change', [
    {'source_id':'../asset_example'}, {'symbol':'000001.SH'},
    {'start':'2026-01-04','end':'2026-01-02'}, {'start':'not-a-date'},
    {'indicators':[dict(instance_id='x',id='sma'),dict(instance_id='x',id='ema')]},
])
def test_rejects_invalid_or_cross_security_requests(tmp_path,change):
    from strategy.application.technical_analysis import TechnicalAnalysisService
    asset(tmp_path)
    with pytest.raises(ValueError):
        TechnicalAnalysisService(tmp_path).analyze(request(**change))


def test_rejects_tampered_hash_and_duplicate_date(tmp_path):
    from strategy.application.technical_analysis import TechnicalAnalysisService
    folder = asset(tmp_path)
    market = folder/'market.csv'
    market.write_text(market.read_text()+'\n')
    with pytest.raises(ValueError,match='哈希'):
        TechnicalAnalysisService(tmp_path).analyze(request())
    original = pd.read_csv(market)
    pd.concat([original, original.iloc[[0]]]).to_csv(market,index=False)
    manifest_path = folder/'market_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['market_sha256'] = hashlib.sha256(market.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='duplicate'):
        TechnicalAnalysisService(tmp_path).analyze(request())


def test_full_history_limit_is_not_silently_truncated(tmp_path):
    from strategy.application.technical_analysis import TechnicalAnalysisService
    asset(tmp_path, with_index=False, days=5001)
    with pytest.raises(ValueError,match='5,000'):
        TechnicalAnalysisService(tmp_path).analyze(request())
