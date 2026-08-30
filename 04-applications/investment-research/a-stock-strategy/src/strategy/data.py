from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd


REQUIRED_MARKET_COLUMNS: Final[tuple[str, ...]] = (
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
)

PRICE_COLUMNS: Final[tuple[str, ...]] = ("open", "high", "low", "close")
BOOL_COLUMNS: Final[tuple[str, ...]] = ("is_suspended", "limit_up", "limit_down")


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y"}:
        return True
    if text in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"cannot parse boolean value: {value!r}")


def _canonicalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    ordered_columns = [column for column in REQUIRED_MARKET_COLUMNS if column in frame.columns]
    ordered_columns.extend(column for column in frame.columns if column not in ordered_columns)
    return frame.loc[:, ordered_columns]


def _complex_rows(values: pd.Series) -> list[int]:
    return [int(index) for index, value in values.items() if np.iscomplexobj(value)]


def validate_market_frame(frame: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_MARKET_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"missing required columns: {', '.join(missing_columns)}")

    parsed_dates = pd.to_datetime(frame["date"], errors="raise")
    if not parsed_dates.is_monotonic_increasing:
        raise ValueError("date column must be monotonic increasing")
    if not parsed_dates.dt.normalize().equals(parsed_dates):
        raise ValueError("date column contains intraday timestamps")

    duplicate_mask = frame.duplicated(subset=["date", "symbol"], keep=False)
    if duplicate_mask.any():
        duplicate_rows = [int(index) for index in frame.index[duplicate_mask]]
        raise ValueError(f"duplicate date/symbol rows: {duplicate_rows}")

    for column in PRICE_COLUMNS:
        raw_values = frame[column]
        complex_rows = _complex_rows(raw_values)
        if complex_rows:
            raise ValueError(f"complex prices in {column} at rows: {complex_rows}")

        numeric_values = pd.to_numeric(raw_values, errors="coerce")
        finite_mask = np.isfinite(numeric_values.to_numpy(dtype="float64", copy=False))
        invalid_mask = ~finite_mask | (numeric_values <= 0).to_numpy()
        bad_rows = [int(index) for index in frame.index[invalid_mask]]
        if bad_rows:
            raise ValueError(f"non-finite or non-positive prices in {column} at rows: {bad_rows}")


class CsvMarketDataProvider:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(self.path)

        frame = pd.read_csv(self.path, converters={column: _parse_bool for column in BOOL_COLUMNS})
        frame["date"] = pd.to_datetime(frame["date"], errors="raise")
        frame = frame.sort_values(["date", "symbol"], kind="stable").reset_index(drop=True)
        frame = _canonicalize_columns(frame)
        validate_market_frame(frame)
        return frame
