from __future__ import annotations

from pathlib import Path
import pandas as pd


REQUIRED_PRICE_COLUMNS = {"date", "symbol", "close", "volume"}
REQUIRED_UNIVERSE_COLUMNS = {"symbol", "name", "asset_type", "group"}


def load_prices(path: str | Path) -> pd.DataFrame:
    """Load long-form adjusted daily data.

    Required columns: date,symbol,close,volume. Prices should be split and
    dividend adjusted to avoid false spread jumps around corporate actions.
    """
    frame = pd.read_csv(path)
    missing = REQUIRED_PRICE_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Price file is missing columns: {sorted(missing)}")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce")
    frame = frame.dropna(subset=["date", "symbol", "close", "volume"])
    frame = frame[(frame.close > 0) & (frame.volume >= 0)]
    frame = frame.sort_values(["date", "symbol"]).drop_duplicates(["date", "symbol"], keep="last")
    return frame


def load_universe(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = REQUIRED_UNIVERSE_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Universe file is missing columns: {sorted(missing)}")
    frame = frame.copy()
    frame["symbol"] = frame.symbol.astype(str).str.upper().str.strip()
    frame["asset_type"] = frame.asset_type.astype(str).str.upper().str.strip()
    if "shortable" not in frame:
        frame["shortable"] = True
    else:
        frame["shortable"] = frame.shortable.astype(str).str.lower().isin(["1", "true", "yes", "y"])
    if frame.symbol.duplicated().any():
        duplicates = frame.loc[frame.symbol.duplicated(), "symbol"].tolist()
        raise ValueError(f"Duplicate universe symbols: {duplicates}")
    return frame.set_index("symbol", drop=False)


def aligned_matrices(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    close = prices.pivot(index="date", columns="symbol", values="close").sort_index()
    volume = prices.pivot(index="date", columns="symbol", values="volume").sort_index()
    return close, volume

