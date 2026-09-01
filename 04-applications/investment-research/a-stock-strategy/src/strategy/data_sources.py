"""真实行情的适配层。

本模块故意不被回测引擎直接依赖网络：上游客户端通过 ``DailyBarFetcher`` 注入，
``AStockDataProvider`` 只负责标准化、缓存和质量检查。因此回测可以继续只读取
本地 CSV，生产环境则可以在每天收盘后运行一次数据刷新。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
from .data import REQUIRED_MARKET_COLUMNS, validate_market_frame


class DailyBarFetcher(Protocol):
    """最小上游协议；实现者只需返回一支证券的日线 DataFrame。"""

    def __call__(self, symbol: str, start: str | None, end: str | None) -> pd.DataFrame: ...


def _symbol(value: object) -> str:
    """统一为六位代码，去掉 ``sh``/``sz`` 等数据源前缀。"""
    text = str(value).strip().lower()
    if len(text) > 2 and text[:2] in {"sh", "sz", "bj"}:
        text = text[2:]
    if not text.isdigit():
        raise ValueError(f"invalid A-share symbol: {value!r}")
    return text.zfill(6)


def normalize_daily_bars(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """把 mootdx/百度常见字段映射到项目的统一日线契约。

    上游通常没有停牌/涨跌停布尔列；为兼容统一 CSV 契约暂时填入 ``False``。
    这个值只表示“数据源未报告限制”，并不能证明证券真实可交易；严肃回测应先
    补齐专门的交易状态数据。复权口径也不从价格列猜测，必须由 provider 的
    ``adjustment`` 元数据记录。
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError(f"empty daily bars for {symbol}")
    aliases = {
        "time": "date", "datetime": "date", "trade_date": "date",
        "vol": "volume", "turnover": "amount",
    }
    result = frame.rename(columns=aliases).copy()
    if "date" not in result:
        raise ValueError("upstream daily bars must contain date/time")
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result["symbol"] = _symbol(symbol)
    for column in ("open", "high", "low", "close", "volume", "amount"):
        if column not in result:
            raise ValueError(f"upstream daily bars missing {column}")
        result[column] = pd.to_numeric(result[column], errors="coerce")
    # 数据源没有交易状态字段时，这些 False 只是契约兼容值，不是可交易性证明。
    # 保留明确注释，避免后续维护者误把“未知”理解为“确认未停牌/未涨跌停”。
    for column in ("is_suspended", "limit_up", "limit_down"):
        if column not in result:
            result[column] = False
    result = result.sort_values("date", kind="stable").drop_duplicates(["date", "symbol"])
    columns = list(REQUIRED_MARKET_COLUMNS)
    extras = [column for column in result.columns if column not in columns]
    result = result[columns + extras].reset_index(drop=True)
    validate_market_frame(result)
    return result


class AStockDataProvider:
    """带 CSV 缓存和失败回退的标准行情 provider。

    ``refresh=False`` 时优先使用缓存，适合可复现回测；``refresh=True`` 才调用上游。
    上游失败时若存在缓存会返回旧数据并在 ``frame.attrs['warnings']`` 留痕，避免因
    网络抖动破坏研究任务，同时不把陈旧数据伪装成最新数据。
    """

    def __init__(self, fetcher: DailyBarFetcher, cache_dir: str | Path | None = None, *, adjustment: str = "none"):
        self.fetcher = fetcher
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.adjustment = adjustment

    def _cache_path(self, symbol: str) -> Path:
        if self.cache_dir is None:
            raise ValueError("cache_dir is required for cached loading")
        return self.cache_dir / f"{symbol}.csv"

    def load(self, symbols: list[str] | tuple[str, ...], *, start: str | None = None,
             end: str | None = None, refresh: bool = False) -> pd.DataFrame:
        warnings: list[str] = []
        frames: list[pd.DataFrame] = []
        for raw_symbol in symbols:
            symbol = _symbol(raw_symbol)
            path = self._cache_path(symbol) if self.cache_dir is not None else None
            cached = None
            if path is not None and path.exists():
                cached = normalize_daily_bars(pd.read_csv(path), symbol)
            frame = None
            if refresh or cached is None:
                try:
                    frame = normalize_daily_bars(self.fetcher(symbol, start, end), symbol)
                    if path is not None:
                        self.cache_dir.mkdir(parents=True, exist_ok=True)
                        frame.to_csv(path, index=False)
                except Exception as error:
                    if cached is None:
                        raise
                    warnings.append(f"{symbol}: stale cache used after upstream failure: {error}")
                    frame = cached
            else:
                frame = cached
            assert frame is not None
            if start is not None:
                frame = frame[frame["date"] >= pd.Timestamp(start)]
            if end is not None:
                frame = frame[frame["date"] <= pd.Timestamp(end)]
            frames.append(frame)
        if not frames:
            raise ValueError("at least one symbol is required")
        result = pd.concat(frames, ignore_index=True).sort_values(["date", "symbol"]).reset_index(drop=True)
        validate_market_frame(result)
        result.attrs["warnings"] = warnings
        result.attrs["adjustment"] = self.adjustment
        return result


class BaiduKlineFetcher:
    """百度股市通日线 adapter；使用 Python 标准库，仅在主动刷新时联网。"""

    url = "https://finance.pae.baidu.com/selfselect/getstockquotation"

    def __init__(self, *, timeout: float = 10.0):
        self.timeout = timeout

    def __call__(self, symbol: str, start: str | None, end: str | None) -> pd.DataFrame:
        """允许直接传入 ``AStockDataProvider(BaiduKlineFetcher(), ...)``。"""
        return self.fetch(symbol, start, end)

    def fetch(self, symbol: str, start: str | None, end: str | None) -> pd.DataFrame:
        params = {
            "all": "1", "isIndex": "false", "isBk": "false", "isBlock": "false",
            "isFutures": "false", "isStock": "true", "newFormat": "1",
            "group": "quotation_kline_ab", "finClientType": "pc", "code": _symbol(symbol),
            "start_time": start or "", "ktype": "1",
        }
        request = Request(self.url + "?" + urlencode(params), headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result = payload.get("Result", {})
        # 百度对有效代码返回字典，对无数据/不支持的代码返回空列表。先检查响应类型，
        # 将上游形态差异转换为稳定、可诊断的 provider 异常。
        if not isinstance(result, dict):
            raise ValueError(f"Baidu returned no daily bars for {_symbol(symbol)}")
        market = result.get("newMarketData", {})
        keys = market.get("keys", [])
        raw_rows = market.get("marketData", "")
        rows = [row.split(",") for row in raw_rows.split(";") if row.strip()]
        if not keys or not rows:
            raise ValueError(f"Baidu returned no daily bars for {_symbol(symbol)}")
        frame = pd.DataFrame(rows, columns=keys)
        for column in ("open", "high", "low", "close", "volume", "amount"):
            if column in frame:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame


__all__ = ["AStockDataProvider", "BaiduKlineFetcher", "DailyBarFetcher", "normalize_daily_bars"]
