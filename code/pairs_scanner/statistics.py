from __future__ import annotations

import math
import numpy as np

try:
    from statsmodels.tsa.stattools import coint as sm_coint
except ImportError:  # reported clearly when exact inference is requested
    sm_coint = None


def ols(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    beta, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ beta
    dof = max(len(y) - x.shape[1], 1)
    sigma2 = float(resid @ resid) / dof
    cov = sigma2 * np.linalg.pinv(x.T @ x)
    return beta, resid, cov


def cointegrating_regression(y: np.ndarray, x: np.ndarray) -> tuple[float, float, np.ndarray]:
    design = np.column_stack([np.ones(len(x)), x])
    beta, resid, _ = ols(y, design)
    return float(beta[0]), float(beta[1]), resid


def adf_statistic(series: np.ndarray, lags: int = 1) -> float:
    """ADF t statistic for gamma in dS = a + gamma*S[-1] + lagged dS."""
    s = np.asarray(series, dtype=float)
    s = s[np.isfinite(s)]
    if len(s) < max(30, lags + 8):
        return float("nan")
    ds = np.diff(s)
    y = ds[lags:]
    columns = [np.ones(len(y)), s[lags:-1]]
    for lag in range(1, lags + 1):
        columns.append(ds[lags - lag : len(ds) - lag])
    design = np.column_stack(columns)
    beta, _, cov = ols(y, design)
    se = math.sqrt(max(float(cov[1, 1]), 0.0))
    return float(beta[1] / se) if se > 0 else float("nan")


def eg_pvalue_approx(adf_stat: float) -> float:
    """Conservative interpolation of common Engle-Granger critical regions.

    This is a screening p-value, not a replacement for a package's MacKinnon
    response-surface p-value. Ranking and FDR calculations use it consistently.
    """
    if not np.isfinite(adf_stat):
        return 1.0
    stats = np.array([-6.0, -5.0, -4.0, -3.34, -3.04, -2.50, -2.00, -1.00, 0.0])
    probs = np.array([0.0001, 0.001, 0.01, 0.05, 0.10, 0.30, 0.60, 0.90, 0.99])
    return float(np.interp(adf_stat, stats, probs))


def cointegration_test(
    y: np.ndarray, x: np.ndarray, lags: int = 1, require_exact: bool = True
) -> tuple[float, float, float]:
    """Engle-Granger statistic, MacKinnon p-value, and 5% critical value."""
    if sm_coint is not None:
        stat, pvalue, critical = sm_coint(
            np.asarray(y, dtype=float),
            np.asarray(x, dtype=float),
            trend="c",
            method="aeg",
            maxlag=lags,
            autolag=None,
        )
        return float(stat), float(pvalue), float(critical[1])
    if require_exact:
        raise RuntimeError(
            "Exact MacKinnon inference requires statsmodels. Install requirements-pairs-scanner.txt "
            "or run with the project-local .venv-pairs Python."
        )
    _, _, spread = cointegrating_regression(y, x)
    stat = adf_statistic(spread, lags)
    return stat, eg_pvalue_approx(stat), -3.34


def half_life(series: np.ndarray) -> float:
    s = np.asarray(series, dtype=float)
    if len(s) < 20:
        return float("nan")
    x = np.column_stack([np.ones(len(s) - 1), s[:-1]])
    beta, _, _ = ols(s[1:], x)
    rho = float(beta[1])
    if not 0.0 < rho < 1.0:
        return float("inf")
    return float(-math.log(2.0) / math.log(rho))


def hurst_exponent(series: np.ndarray) -> float:
    s = np.asarray(series, dtype=float)
    lags = np.arange(2, min(50, len(s) // 4))
    if len(lags) < 5:
        return float("nan")
    tau = np.array([np.std(s[lag:] - s[:-lag], ddof=1) for lag in lags])
    valid = tau > 0
    if valid.sum() < 5:
        return float("nan")
    slope = np.polyfit(np.log(lags[valid]), np.log(tau[valid]), 1)[0]
    return float(np.clip(slope, 0.0, 1.0))


def zero_crossing_rate(series: np.ndarray) -> float:
    centered = np.asarray(series, dtype=float) - np.nanmean(series)
    if len(centered) < 2:
        return float("nan")
    return float(np.mean(centered[:-1] * centered[1:] <= 0))


def benjamini_hochberg(pvalues: np.ndarray) -> np.ndarray:
    p = np.asarray(pvalues, dtype=float)
    n = len(p)
    if n == 0:
        return p.copy()
    order = np.argsort(p)
    ranked = p[order]
    adjusted = ranked * n / np.arange(1, n + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty(n)
    result[order] = np.clip(adjusted, 0.0, 1.0)
    return result
