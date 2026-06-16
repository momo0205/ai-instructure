import logging
from typing import Dict, List

import numpy as np

from core.exchange import OKXExchange

logger = logging.getLogger(__name__)


class MarketDataCollector:
    def __init__(self, exchange: OKXExchange):
        self.exchange = exchange

    def get_top_coins_by_volume(self, limit: int = 50, quote: str = "USDT") -> List[dict]:
        try:
            tickers = self.exchange.fetch_tickers()
        except Exception as e:
            logger.error(f"Failed to fetch tickers: {e}")
            return []

        usdt_pairs = {}
        for k, v in tickers.items():
            if not k.endswith(f"/{quote}"):
                continue
            qv = v.get("quoteVolume")
            if qv is None:
                continue
            usdt_pairs[k] = v

        sorted_pairs = sorted(
            usdt_pairs.items(),
            key=lambda x: x[1].get("quoteVolume", 0) or 0,
            reverse=True,
        )

        return [
            {
                "symbol": symbol,
                "last": data.get("last", 0),
                "change_24h": data.get("percentage", 0) or 0,
                "volume_24h": data.get("quoteVolume", 0) or 0,
                "high_24h": data.get("high", 0) or 0,
                "low_24h": data.get("low", 0) or 0,
            }
            for symbol, data in sorted_pairs[:limit]
        ]

    def calculate_indicators(self, symbol: str) -> dict:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, "1h", limit=100)
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return self._empty_indicators()

        if len(ohlcv) < 24:
            return self._empty_indicators()

        closes = np.array([c[4] for c in ohlcv], dtype=np.float64)
        highs = np.array([c[2] for c in ohlcv], dtype=np.float64)
        lows = np.array([c[3] for c in ohlcv], dtype=np.float64)
        volumes = np.array([c[5] for c in ohlcv], dtype=np.float64)

        adx = self._calculate_adx(highs, lows, closes)

        bb_mid = float(np.mean(closes[-20:]))
        bb_std = float(np.std(closes[-20:]))
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        bb_width = (bb_upper - bb_lower) / bb_mid if bb_mid > 0 else 0.0

        if len(closes) >= 24:
            returns = np.diff(np.log(closes[-24:]))
            volatility = float(np.std(returns) * np.sqrt(365 * 24))
            price_change_24h = float((closes[-1] - closes[-24]) / closes[-24] * 100)
        else:
            volatility = 0.0
            price_change_24h = 0.0

        vol_ma_short = float(np.mean(volumes[-5:])) if len(volumes) >= 5 else 0.0
        vol_ma_long = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else 0.0
        vol_trend = vol_ma_short / vol_ma_long if vol_ma_long > 0 else 1.0

        return {
            "adx": round(adx, 2),
            "bb_width": round(bb_width, 4),
            "bb_upper": round(bb_upper, 4),
            "bb_lower": round(bb_lower, 4),
            "current_price": round(float(closes[-1]), 4),
            "volatility": round(volatility, 4),
            "volume_trend": round(vol_trend, 4),
            "price_change_24h": round(price_change_24h, 2),
        }

    def _calculate_adx(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        n = len(highs)
        if n < period + 1:
            return 0.0

        tr = np.zeros(n - 1)
        plus_dm = np.zeros(n - 1)
        minus_dm = np.zeros(n - 1)

        for i in range(1, n):
            tr[i - 1] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            up_move = highs[i] - highs[i - 1]
            down_move = lows[i - 1] - lows[i]
            plus_dm[i - 1] = up_move if (up_move > down_move and up_move > 0) else 0.0
            minus_dm[i - 1] = down_move if (down_move > up_move and down_move > 0) else 0.0

        atr = float(np.mean(tr[:period]))
        if atr == 0:
            return 0.0

        plus_di = 100.0 * float(np.mean(plus_dm[:period])) / atr
        minus_di = 100.0 * float(np.mean(minus_dm[:period])) / atr
        di_sum = plus_di + minus_di
        dx = 100.0 * abs(plus_di - minus_di) / di_sum if di_sum > 0 else 0.0

        return dx

    @staticmethod
    def _empty_indicators() -> dict:
        return {
            "adx": 0.0,
            "bb_width": 0.0,
            "bb_upper": 0.0,
            "bb_lower": 0.0,
            "current_price": 0.0,
            "volatility": 0.0,
            "volume_trend": 1.0,
            "price_change_24h": 0.0,
        }
