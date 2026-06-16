import math
import time
import logging
from functools import wraps
from typing import Optional

import ccxt

from config.settings import settings

logger = logging.getLogger(__name__)


def rate_limit_retry(max_retries: int = 3, base_delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except ccxt.RateLimitExceeded:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate limited, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                except (ccxt.NetworkError, ccxt.ExchangeNotAvailable) as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Network error: {e}, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
            return None

        return wrapper

    return decorator


def _require_connected(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.connected:
            logger.debug(f"Skipping {func.__name__}: exchange not connected")
            return {} if "balance" in func.__name__ or "ticker" in func.__name__ else ([] if "orders" in func.__name__ or "ohlcv" in func.__name__ else 0.0 if "free" in func.__name__ else None)
        return func(self, *args, **kwargs)

    return wrapper


class OKXExchange:
    def __init__(self):
        self.connected = False

        config = {
            "apiKey": settings.OKX_API_KEY,
            "secret": settings.OKX_SECRET,
            "password": settings.OKX_PASSWORD,
            "enableRateLimit": True,
            "timeout": 30000,
            "options": {"defaultType": "spot"},
        }
        if settings.OKX_PROXY:
            config["proxies"] = {
                "http": settings.OKX_PROXY,
                "https": settings.OKX_PROXY,
            }

        self.exchange = ccxt.okx(config)

        if settings.OKX_SANDBOX:
            self.exchange.set_sandbox_mode(True)
            logger.info("OKX Sandbox mode enabled")

        self._last_request_time = 0.0
        self._min_interval = 0.12

        self._test_connection()

    def _test_connection(self):
        try:
            old_timeout = self.exchange.timeout
            self.exchange.timeout = 5000
            self.exchange.fetch_time()
            self.connected = True
            logger.info("OKX exchange connected successfully")
        except Exception as e:
            self.connected = False
            logger.warning(
                f"OKX exchange unreachable: {e}. "
                f"Dashboard will work but trading is disabled. "
                f"Set OKX_PROXY if behind firewall."
            )
        finally:
            self.exchange.timeout = old_timeout

    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    @_require_connected
    @rate_limit_retry(max_retries=1, base_delay=0.5)
    def fetch_balance(self, params: Optional[dict] = None) -> dict:
        self._throttle()
        p = params or {"type": "spot"}
        return self.exchange.fetch_balance(p)

    @_require_connected
    @rate_limit_retry(max_retries=1, base_delay=0.5)
    def fetch_free_balance(self, currency: str = "USDT") -> float:
        self._throttle()
        balance = self.exchange.fetch_balance({"type": "spot"})
        return float(balance.get(currency, {}).get("free", 0) or 0)

    @_require_connected
    @rate_limit_retry(max_retries=1, base_delay=0.5)
    def fetch_ticker(self, symbol: str) -> dict:
        self._throttle()
        return self.exchange.fetch_ticker(symbol)

    @_require_connected
    @rate_limit_retry(max_retries=1, base_delay=0.5)
    def fetch_tickers(self) -> dict:
        self._throttle()
        return self.exchange.fetch_tickers()

    @_require_connected
    @rate_limit_retry(max_retries=1, base_delay=0.5)
    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list:
        self._throttle()
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    @_require_connected
    @rate_limit_retry(max_retries=2, base_delay=1.0)
    def create_limit_order(self, symbol: str, side: str, amount: float, price: float) -> dict:
        self._throttle()
        params = {"tdMode": "cash"}
        return self.exchange.create_order(symbol, "limit", side, amount, price, params)

    @_require_connected
    @rate_limit_retry(max_retries=2, base_delay=1.0)
    def create_market_order(self, symbol: str, side: str, amount: float) -> dict:
        self._throttle()
        params = {"tdMode": "cash"}
        return self.exchange.create_order(symbol, "market", side, amount, None, params)

    @_require_connected
    @rate_limit_retry(max_retries=2, base_delay=1.0)
    def cancel_order(self, order_id: str, symbol: str) -> dict:
        self._throttle()
        return self.exchange.cancel_order(order_id, symbol)

    @_require_connected
    @rate_limit_retry(max_retries=2, base_delay=1.0)
    def cancel_all_orders(self, symbol: str) -> list:
        self._throttle()
        return self.exchange.cancel_all_orders(symbol)

    @_require_connected
    @rate_limit_retry(max_retries=1, base_delay=0.5)
    def fetch_order(self, order_id: str, symbol: str) -> dict:
        self._throttle()
        return self.exchange.fetch_order(order_id, symbol)

    @_require_connected
    @rate_limit_retry(max_retries=1, base_delay=0.5)
    def fetch_open_orders(self, symbol: Optional[str] = None) -> list:
        self._throttle()
        return self.exchange.fetch_open_orders(symbol)

    @_require_connected
    @rate_limit_retry(max_retries=1, base_delay=0.5)
    def fetch_closed_orders(self, symbol: str, limit: int = 50) -> list:
        self._throttle()
        return self.exchange.fetch_closed_orders(symbol, limit=limit)

    def get_market(self, symbol: str) -> dict:
        return self.exchange.market(symbol)

    def get_price_precision(self, symbol: str) -> int:
        market = self.exchange.market(symbol)
        tick_size = market["precision"]["price"]
        if isinstance(tick_size, float) and tick_size < 1:
            return len(str(tick_size).rstrip("0").split(".")[-1])
        return 0

    def get_amount_precision(self, symbol: str) -> float:
        market = self.exchange.market(symbol)
        return market["precision"]["amount"]

    def get_min_amount(self, symbol: str) -> float:
        market = self.exchange.market(symbol)
        return market["limits"]["amount"]["min"] or 0.0

    def round_price(self, symbol: str, price: float) -> float:
        prec = self.get_price_precision(symbol)
        return round(price, prec)

    def round_amount(self, symbol: str, amount: float) -> float:
        min_amt = self.get_min_amount(symbol)
        prec = self.get_amount_precision(symbol)
        if prec is not None and prec > 0:
            steps = math.floor(amount / prec)
            amount = round(steps * prec, 8)
        if amount < min_amt:
            return 0.0
        return amount
