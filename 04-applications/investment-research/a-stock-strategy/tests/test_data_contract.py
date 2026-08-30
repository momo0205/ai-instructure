from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from strategy.config import load_config
from strategy.data import CsvMarketDataProvider, validate_market_frame


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_validate_market_frame_rejects_missing_required_columns() -> None:
    frame = _frame(
        [
            {
                "date": "2026-08-01",
                "symbol": "588000.SH",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 1000,
                "amount": 1000,
                "is_suspended": False,
                "limit_up": False,
            }
        ]
    )

    with pytest.raises(ValueError, match="missing required columns"):
        validate_market_frame(frame)


def test_validate_market_frame_rejects_duplicate_date_symbol() -> None:
    frame = _frame(
        [
            {
                "date": "2026-08-01",
                "symbol": "588000.SH",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 1000,
                "amount": 1000,
                "is_suspended": False,
                "limit_up": False,
                "limit_down": False,
            },
            {
                "date": "2026-08-01",
                "symbol": "588000.SH",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 1000,
                "amount": 1000,
                "is_suspended": False,
                "limit_up": False,
                "limit_down": False,
            },
        ]
    )

    with pytest.raises(ValueError, match="duplicate"):
        validate_market_frame(frame)


def test_validate_market_frame_rejects_non_positive_prices() -> None:
    frame = _frame(
        [
            {
                "date": "2026-08-01",
                "symbol": "588000.SH",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 1000,
                "amount": 1000,
                "is_suspended": False,
                "limit_up": False,
                "limit_down": False,
            },
            {
                "date": "2026-08-02",
                "symbol": "588000.SH",
                "open": 0.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.0,
                "volume": 1000,
                "amount": 1000,
                "is_suspended": False,
                "limit_up": False,
                "limit_down": False,
            },
        ]
    )

    with pytest.raises(ValueError, match="non-positive"):
        validate_market_frame(frame)


def test_load_config_parses_baseline_toml() -> None:
    config_path = Path("configs/baseline.toml")

    config = load_config(config_path)

    assert config.data.source == "csv"
    assert config.data.path == "data/sample/market.csv"
    assert config.backtest.initial_cash == 100000.0
    assert config.strategy.name == "fixed_asset"


def test_csv_market_data_provider_loads_sample_market_data() -> None:
    provider = CsvMarketDataProvider(Path("data/sample/market.csv"))

    frame = provider.load()

    assert not frame.empty
    assert list(frame.columns) == [
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "is_suspended",
        "limit_up",
        "limit_down",
    ]
