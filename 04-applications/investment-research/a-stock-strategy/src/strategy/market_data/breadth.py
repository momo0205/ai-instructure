"""Explicit daily market breadth, never inferred from the ETF candidate pool."""
from pathlib import Path
import numpy as np
import pandas as pd


def load_breadth(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"date", "declining_count", "total_count", "source"}
    if missing := required - set(frame):
        raise ValueError(f"breadth missing columns: {', '.join(sorted(missing))}")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    if frame.empty or frame.date.isna().any() or not frame.date.eq(frame.date.dt.normalize()).all():
        raise ValueError("breadth must contain valid daily dates")
    if frame.date.duplicated().any():
        raise ValueError("duplicate breadth dates")
    for column in ("declining_count", "total_count"):
        values = pd.to_numeric(frame[column], errors="raise")
        if not (np.isfinite(values).all() and values.ge(0).all() and values.eq(values.round()).all()):
            raise ValueError(f"invalid breadth count: {column}")
        frame[column] = values.astype(int)
    if (frame.declining_count > frame.total_count).any() or (frame.total_count <= 0).any():
        raise ValueError("breadth declining_count must not exceed positive total_count")
    if frame.source.isna().any() or frame.source.astype(str).str.strip().eq("").any():
        raise ValueError("breadth source is required")
    return frame.sort_values("date").reset_index(drop=True)


def attach_breadth(data, breadth, index_symbol):
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    if "declining_count" in frame:
        raise ValueError("market data already contains declining_count; remove ambiguous duplicate source")
    renamed = breadth.rename(columns={"total_count": "breadth_total_count", "source": "breadth_source"})
    frame = frame.merge(renamed, on="date", how="left", validate="many_to_one")
    columns = [c for c in renamed if c != "date"]
    frame.loc[frame.symbol != index_symbol, columns] = np.nan
    return frame
