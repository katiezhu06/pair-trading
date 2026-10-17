from __future__ import annotations

import numpy as np
import pandas as pd


def make_demo_data(days: int = 1100, seed: int = 17) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic synthetic data for smoke tests; never use for investment decisions."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-01", periods=days)
    factor_a = np.cumsum(rng.normal(0.0003, 0.012, days))
    factor_b = np.cumsum(rng.normal(0.0002, 0.010, days))
    noise = np.zeros(days)
    for i in range(1, days):
        noise[i] = 0.88 * noise[i - 1] + rng.normal(0, 0.009)
    log_prices = {
        "ALFA": 4.7 + factor_a + noise,
        "BETA": 4.5 + factor_a,
        "GAMA": 4.4 + factor_b + rng.normal(0, 0.015, days),
        "DELT": 4.2 + factor_b,
        "RAND": 4.3 + np.cumsum(rng.normal(0.0002, 0.018, days)),
    }
    rows = []
    for symbol, log_price in log_prices.items():
        for date, price in zip(dates, np.exp(log_price)):
            rows.append({"date": date, "symbol": symbol, "close": price, "volume": 2_000_000})
    prices = pd.DataFrame(rows)
    universe = pd.DataFrame(
        [
            ("ALFA", "Synthetic Alpha", "STK", "Synthetic A", True),
            ("BETA", "Synthetic Beta", "STK", "Synthetic A", True),
            ("GAMA", "Synthetic Gamma", "ETF", "Synthetic B", True),
            ("DELT", "Synthetic Delta", "ETF", "Synthetic B", True),
            ("RAND", "Synthetic Random Walk", "STK", "Synthetic A", True),
        ], columns=["symbol", "name", "asset_type", "group", "shortable"]
    ).set_index("symbol", drop=False)
    return prices, universe

