import json
import pandas as pd
import pytest


def api():
    from strategy.ingest import build_breadth, download_tushare_daily
    return build_breadth, download_tushare_daily


def daily(rows=None):
    return pd.DataFrame(rows or [
        ['20240102', '600000.SH', -1],
        ['20240102', '000001.SZ', 0],
        ['20240102', '920001.BJ', -2],
    ], columns=['trade_date', 'ts_code', 'pct_chg'])


def test_breadth_counts_three_markets_and_only_negative_returns():
    build, _ = api()
    row = build(daily(), 'tushare.daily', min_daily_records=1).iloc[0]
    assert row['date'] == '2024-01-02'
    assert row['declining_count'] == 2
    assert row['total_count'] == 3
    assert (row.sh_count, row.sz_count, row.bj_count) == (1, 1, 1)
    assert row.source == 'tushare.daily'


@pytest.mark.parametrize('code', ['510300.SH', '000001.SH', '900001.SH', '200001.SZ', '600000.SZ', '920001.SH', '123456.BJ'])
def test_breadth_rejects_non_a_share_and_mismatched_codes(code):
    build, _ = api()
    with pytest.raises(ValueError, match='A 股'):
        build(daily([['20240102', code, -1]]), 'csv', min_daily_records=1)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -101, 'oops', True])
def test_breadth_rejects_invalid_return(value):
    build, _ = api()
    with pytest.raises(ValueError, match='pct_chg'):
        build(daily([['20240102', '600000.SH', value]]), 'csv', min_daily_records=1)


@pytest.mark.parametrize('date', ['20240230', '2024/01/02', '2024-1-2', '20240102 12:00'])
def test_breadth_rejects_invalid_dates(date):
    build, _ = api()
    with pytest.raises(ValueError, match='日期'):
        build(daily([[date, '600000.SH', -1]]), 'csv', min_daily_records=1)


def test_breadth_normalizes_dates_before_duplicate_check():
    build, _ = api()
    with pytest.raises(ValueError, match='重复'):
        build(daily([['20240102', '600000.SH', -1], ['2024-01-02', '600000.SH', -1]]), 'csv', min_daily_records=1)


def test_breadth_rejects_partial_list_by_default():
    build, _ = api()
    with pytest.raises(ValueError, match='4000'):
        build(daily(), 'csv')


def response(rows):
    return {'code': 0, 'msg': None, 'data': {'fields': ['trade_date', 'ts_code', 'pct_chg'], 'items': rows}}


def test_download_paginates_and_preserves_raw_and_manifest(tmp_path):
    _, download = api()
    requests, waits = [], []
    # Generate 6000 syntactically valid distinct stocks to exercise page boundary.
    page = [['20240102', f'600{i:03d}.SH', -1] for i in range(1000)]
    for prefix in ['601', '603', '605', '688', '000']:
        exchange = 'SZ' if prefix == '000' else 'SH'
        page += [['20240102', f'{prefix}{i:03d}.{exchange}', 1] for i in range(1000)]
    def requester(payload):
        requests.append(payload)
        return response(page if payload['params']['offset'] == 0 else [['20240102', '920001.BJ', -1]])
    result = download('2024-01-02', '2024-01-02', tmp_path, token='secret', requester=requester, sleeper=waits.append)
    frame = pd.read_csv(result['breadth'])
    assert frame.iloc[0].total_count == 6001
    assert frame.iloc[0].declining_count == 1001
    assert [r['params']['offset'] for r in requests] == [0, 6000]
    assert all(r['params']['limit'] == 6000 for r in requests)
    assert waits and all(w >= 1.3 for w in waits)
    manifest = json.loads(result['manifest'].read_text())
    assert manifest['coverage_dates'] == ['2024-01-02']
    assert manifest['complete_universe_verified'] is False
    assert 'secret' not in result['manifest'].read_text()
    assert len(list(result['raw_dir'].glob('*.csv'))) == 1


def test_download_records_empty_weekday_but_skips_weekend(tmp_path):
    _, download = api()
    calls = []
    def requester(payload):
        calls.append(payload['params']['trade_date'])
        return response([])
    result = download('2024-01-05', '2024-01-08', tmp_path, token='secret', requester=requester, sleeper=lambda _: None)
    assert calls == ['20240105', '20240108']
    manifest = json.loads(result['manifest'].read_text())
    assert manifest['empty_dates'] == ['2024-01-05', '2024-01-08']
    assert pd.read_csv(result['breadth']).empty


def test_download_rejects_api_error_and_does_not_publish(tmp_path):
    _, download = api()
    with pytest.raises(ValueError, match='Tushare.*权限'):
        download('20240102', '20240102', tmp_path, token='secret', requester=lambda _: {'code': -2001, 'msg': '权限不足 secret'}, sleeper=lambda _: None)
    assert not (tmp_path / 'breadth.csv').exists()


def test_download_error_redacts_token(tmp_path):
    _, download = api()
    with pytest.raises(ValueError) as exc:
        download('20240102', '20240102', tmp_path, token='secret', requester=lambda _: {'code': -1, 'msg': 'bad secret'}, sleeper=lambda _: None)
    assert 'secret' not in str(exc.value)


def test_download_missing_token_fails_without_network_or_writes(tmp_path, monkeypatch):
    _, download = api()
    monkeypatch.delenv('TUSHARE_TOKEN', raising=False)
    with pytest.raises(ValueError, match='TUSHARE_TOKEN'):
        download('20240102', '20240102', tmp_path / 'new', requester=lambda _: pytest.fail('network called'))
    assert not (tmp_path / 'new').exists()


def test_download_rejects_wrong_day_and_does_not_publish(tmp_path):
    _, download = api()
    with pytest.raises(ValueError, match='日期'):
        download('20240102', '20240102', tmp_path, token='secret', requester=lambda _: response([['20240103', '600000.SH', -1]]), sleeper=lambda _: None, min_daily_records=1)
    assert not (tmp_path / 'breadth.csv').exists()
