from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import pandas as pd


def _epoch(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())


def _download_symbol(symbol: str, start: date, end: date) -> list[dict]:
    query = urlencode(
        {
            "period1": _epoch(start),
            "period2": _epoch(end + timedelta(days=1)),
            "interval": "1d",
            "events": "div,splits",
            "includeAdjustedClose": "true",
        }
    )
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}"
    request = Request(url, headers={"User-Agent": "pairs-scanner/1.0 research"})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
            break
        except Exception as exc:  # retry transient HTTP/network failures
            if attempt == 3:
                raise RuntimeError(f"Could not download {symbol}: {exc}") from exc
            time.sleep(1.5 * (attempt + 1))
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose", quote.get("close", []))
    volumes = quote.get("volume", [])
    rows = []
    for timestamp, close, volume in zip(timestamps, adjusted, volumes):
        if close is not None and volume is not None:
            rows.append(
                {
                    "date": datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat(),
                    "symbol": symbol.upper(),
                    "close": float(close),
                    "volume": float(volume),
                }
            )
    return rows


def download_yahoo_adjusted(
    symbols: list[str], start: date, end: date, max_workers: int = 8
) -> pd.DataFrame:
    """Download adjusted daily close/volume from Yahoo's public chart endpoint."""
    rows: list[dict] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_symbols = {pool.submit(_download_symbol, symbol, start, end): symbol for symbol in symbols}
        for future in as_completed(future_symbols):
            symbol = future_symbols[future]
            try:
                rows.extend(future.result())
            except RuntimeError as exc:
                failures.append(str(exc))
    if failures:
        preview = "; ".join(failures[:5])
        raise RuntimeError(f"Failed to download {len(failures)} symbols. {preview}")
    if not rows:
        raise RuntimeError("The data provider returned no daily bars")
    return pd.DataFrame(rows).sort_values(["date", "symbol"])
