from io import BytesIO

import pytest

from strategy.market_provider import CallableMarketDataProvider, TencentMarketDataProvider


def test_tencent_resolve_checks_response_and_decodes_name():
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        return BytesIO('v_sz002015="51~协鑫能科~002015~10";'.encode('gbk'))

    assert TencentMarketDataProvider(opener=opener).resolve('002015.SZ') == {
        'symbol': '002015.SZ', 'name': '协鑫能科', 'kind': 'stock',
    }
    assert calls == [('https://qt.gtimg.cn/q=sz002015', 15)]


@pytest.mark.parametrize('payload', ['v_sz002015="51~名称~002016~10";', 'v_sz002015="51~ ~002015~10";', ''])
def test_tencent_resolve_rejects_unconfirmed_symbol(payload):
    provider = TencentMarketDataProvider(opener=lambda *args, **kwargs: BytesIO(payload.encode('gbk')))
    with pytest.raises(ValueError, match='数据源未确认'):
        provider.resolve('002015.SZ')


def test_tencent_download_delegates_original_contract(monkeypatch, tmp_path):
    calls = []
    def download(*args, **kwargs):
        calls.append((args, kwargs))
        return {'market': 'market.csv'}
    monkeypatch.setattr('strategy.market_provider.download_market', download)
    assert TencentMarketDataProvider().download('2024-01-01', '2024-01-02', tmp_path,
                                              symbols=['002015.SZ'], adjustment='qfq') == {'market': 'market.csv'}
    assert calls == [(('2024-01-01', '2024-01-02', tmp_path), {'symbols': ['002015.SZ'], 'adjustment': 'qfq'})]


def test_callable_provider_preserves_injected_functions(tmp_path):
    calls = []
    def downloader(*args, **kwargs):
        calls.append((args, kwargs))
        return 'downloaded'
    provider = CallableMarketDataProvider(downloader, lambda symbol: {'symbol': symbol, 'name': '测试'})
    assert provider.resolve('002015.SZ') == {'symbol': '002015.SZ', 'name': '测试'}
    assert provider.download('2024-01-01', '2024-01-02', tmp_path, ['002015.SZ'], 'none') == 'downloaded'
    assert calls == [(('2024-01-01', '2024-01-02', tmp_path), {'symbols': ['002015.SZ'], 'adjustment': 'none'})]
