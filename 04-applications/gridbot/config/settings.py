from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    APP_NAME: str = "GridBot"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = "sqlite:///./data/gridbot.db"

    OKX_API_KEY: str = ""
    OKX_SECRET: str = ""
    OKX_PASSWORD: str = ""
    OKX_SANDBOX: bool = True
    OKX_RATE_LIMIT_RPM: int = 10
    OKX_PROXY: str = ""

    DEFAULT_GRID_TYPE: str = "arithmetic"
    DEFAULT_GRID_COUNT: int = 20
    DEFAULT_UPPER_BUFFER: float = 0.05
    DEFAULT_LOWER_BUFFER: float = 0.05
    MAX_GRIDS_PER_COIN: int = 50
    MAX_CONCURRENT_GRIDS: int = 5

    MAX_INVESTMENT_PER_GRID_USDT: float = 1000.0
    MAX_TOTAL_EXPOSURE_USDT: float = 5000.0
    STOP_LOSS_BREACH_PCT: float = 0.03
    DAILY_LOSS_LIMIT_USDT: float = 200.0
    COIN_WHITELIST: list[str] = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]

    LLM_PROVIDER: str = "deepseek"
    LLM_MODEL: str = "deepseek-chat"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com"
    AI_COIN_SELECTION_INTERVAL_H: int = 4
    AI_REGIME_CHECK_INTERVAL_M: int = 15
    AI_SENTIMENT_INTERVAL_H: int = 4

    ENGINE_TICK_INTERVAL_S: int = 5
    QUOTE_CURRENCY: str = "USDT"

    CRYPTOPANIC_API_KEY: str = ""

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""


settings = Settings()
