from __future__ import annotations

import pandas as pd
import pytest

from strategy.data import CsvMarketDataProvider
from strategy.data_sources import (
    AStockDataProvider, BaiduKlineFetcher, MootdxIndexFetcher, create_mootdx_client,
)


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": ["2026-08-03", "2026-08-04"],
            "open": [1.0, 1.1],
            "high": [1.2, 1.3],
            "low": [0.9, 1.0],
            "close": [1.1, 1.2],
            "volume": [100, 120],
            "amount": [1100, 1400],
        }
    )


def test_provider_normalizes_upstream_fields_and_caches(tmp_path):
    calls: list[str] = []

    def fetch(symbol: str, start: str | None, end: str | None) -> pd.DataFrame:
        calls.append(symbol)
        return _bars()

    provider = AStockDataProvider(fetch, cache_dir=tmp_path, adjustment="none")
    frame = provider.load(["510688"], start="2026-08-03", end="2026-08-04")

    assert calls == ["510688"]
    assert list(frame.columns[:11]) == [
        "date", "symbol", "open", "high", "low", "close", "volume",
        "amount", "is_suspended", "limit_up", "limit_down",
    ]
    assert frame["symbol"].tolist() == ["510688", "510688"]
    assert frame["is_suspended"].tolist() == [False, False]
    assert (tmp_path / "510688.csv").exists()

    # 第二次读取命中本地缓存，回测/研究阶段不需要再次联网。
    cached = AStockDataProvider(lambda *_: pytest.fail("unexpected network call"), cache_dir=tmp_path)
    pd.testing.assert_frame_equal(cached.load(["510688"]), frame)


def test_provider_uses_stale_cache_when_refresh_fails(tmp_path):
    AStockDataProvider(lambda *_: _bars(), cache_dir=tmp_path).load(["600000"])

    def broken(*_args):
        raise OSError("upstream unavailable")

    frame = AStockDataProvider(broken, cache_dir=tmp_path).load(["600000"], refresh=True)
    assert len(frame) == 2
    assert any("stale cache" in warning for warning in frame.attrs["warnings"])


def test_provider_rejects_malformed_upstream_prices():
    bad = _bars()
    bad.loc[0, "close"] = 0
    with pytest.raises(ValueError, match="non-positive"):
        AStockDataProvider(lambda *_: bad).load(["000001"])


def test_csv_provider_preserves_leading_zero_in_symbol(tmp_path):
    path = tmp_path / "market.csv"
    frame = _bars().rename(columns={"time": "date"}).assign(
        symbol="000001", is_suspended=False, limit_up=False, limit_down=False
    )
    frame.to_csv(path, index=False)

    loaded = CsvMarketDataProvider(path).load()

    assert loaded["symbol"].tolist() == ["000001", "000001"]


def test_baidu_fetcher_parses_keyed_rows(monkeypatch):
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            import json
            return json.dumps({
                "Result": {
                    "newMarketData": {
                        "keys": ["time", "open", "close", "high", "low", "volume", "amount"],
                        "marketData": "2026-08-03,1,1.1,1.2,0.9,100,1100;",
                    }
                }
            }).encode()

    def fake_urlopen(request, **kwargs):
        seen["accept"] = request.get_header("Accept")
        seen["origin"] = request.get_header("Origin")
        seen["referer"] = request.get_header("Referer")
        return Response()

    monkeypatch.setattr("strategy.data_sources.urlopen", fake_urlopen)
    frame = BaiduKlineFetcher().fetch("000001", None, None)
    assert frame.iloc[0]["time"] == "2026-08-03"
    assert frame.iloc[0]["close"] == 1.1
    assert seen == {
        "accept": "application/vnd.finance-web.v1+json",
        "origin": "https://gushitong.baidu.com",
        "referer": "https://gushitong.baidu.com/",
    }


def test_baidu_fetcher_reports_empty_result_as_source_error(monkeypatch):
    """无行情代码应得到可诊断的数据源错误，而不是泄漏内部 AttributeError。"""

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            import json
            return json.dumps({"ResultCode": 0, "Result": []}).encode()

    monkeypatch.setattr("strategy.data_sources.urlopen", lambda *args, **kwargs: Response())

    with pytest.raises(ValueError, match="no daily bars for 510688"):
        BaiduKlineFetcher().fetch("510688", None, None)


def test_mootdx_index_fetcher_uses_index_endpoint_and_normalizes():
    calls = []

    class FakeClient:
        def index(self, **kwargs):
            calls.append(kwargs)
            return pd.DataFrame({
                "datetime": ["2026-08-03", "2026-08-04"],
                "open": [4005, 3990], "high": [4010, 4000], "low": [3980, 3970],
                "close": [3990, 3980], "vol": [100, 110], "amount": [1, 1],
            })

    frame = MootdxIndexFetcher(FakeClient(), page_size=800).fetch("000001", None, None)

    assert calls[0]["symbol"] == "000001"
    assert frame["symbol"].tolist() == ["000001", "000001"]
    assert frame["close"].tolist() == [3990, 3980]


def test_mootdx_client_skips_reachable_server_that_returns_empty_data():
    made = []

    class Client:
        def __init__(self, valid):
            self.valid = valid

        def bars(self, **_kwargs):
            return _bars().head(1) if self.valid else pd.DataFrame()

    def factory(**kwargs):
        made.append(kwargs)
        return Client(kwargs.get("server") == ("good", 7709))

    client = create_mootdx_client(
        quotes_factory=factory,
        servers=(("empty", 7709), ("good", 7709)),
        probe=lambda *_args: True,
    )

    assert client.valid
    assert [call["server"] for call in made] == [("empty", 7709), ("good", 7709)]


def test_mootdx_client_uses_library_fallbacks_after_server_candidates_fail():
    calls = []

    class Client:
        def __init__(self, valid):
            self.valid = valid

        def bars(self, **_kwargs):
            return _bars().head(1) if self.valid else pd.DataFrame()

    def factory(**kwargs):
        calls.append(kwargs)
        return Client(kwargs.get("bestip") is True)

    client = create_mootdx_client(
        quotes_factory=factory, servers=(("down", 7709),), probe=lambda *_args: False,
    )

    assert client.valid
    assert calls == [{"market": "std", "bestip": True}]
