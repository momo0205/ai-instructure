from __future__ import annotations

import pandas as pd
import pytest

from strategy.data_sources import AStockDataProvider, BaiduKlineFetcher


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


def test_baidu_fetcher_parses_keyed_rows(monkeypatch):
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

    monkeypatch.setattr("strategy.data_sources.urlopen", lambda *args, **kwargs: Response())
    frame = BaiduKlineFetcher().fetch("000001", None, None)
    assert frame.iloc[0]["time"] == "2026-08-03"
    assert frame.iloc[0]["close"] == 1.1
