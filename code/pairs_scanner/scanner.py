from __future__ import annotations

from itertools import combinations
import math
import numpy as np
import pandas as pd

from .backtest import walk_forward_backtest
from .config import ScannerConfig
from .data import aligned_matrices
from .statistics import (
    benjamini_hochberg,
    cointegration_test,
    cointegrating_regression,
    half_life,
    hurst_exponent,
    zero_crossing_rate,
)


def _eligible_symbols(
    close: pd.DataFrame, volume: pd.DataFrame, universe: pd.DataFrame, cfg: ScannerConfig
) -> tuple[list[str], pd.DataFrame]:
    rows = []
    common = sorted(set(close.columns) & set(volume.columns) & set(universe.index))
    for symbol in common:
        valid = close[symbol].notna() & volume[symbol].notna()
        recent = pd.DataFrame({"close": close.loc[valid, symbol], "volume": volume.loc[valid, symbol]}).tail(
            cfg.liquidity_lookback
        )
        adv = float((recent.close * recent.volume).mean()) if len(recent) else 0.0
        last_price = float(recent.close.iloc[-1]) if len(recent) else 0.0
        rows.append(
            {
                "symbol": symbol,
                "history_days": int(valid.sum()),
                "avg_dollar_volume": adv,
                "last_price": last_price,
                "shortable": bool(universe.loc[symbol, "shortable"]),
            }
        )
    diagnostics = pd.DataFrame(rows).set_index("symbol") if rows else pd.DataFrame()
    if diagnostics.empty:
        return [], diagnostics
    mask = (
        (diagnostics.history_days >= cfg.min_history_days)
        & (diagnostics.avg_dollar_volume >= cfg.min_avg_dollar_volume)
        & (diagnostics.last_price >= cfg.min_price)
        & diagnostics.shortable
    )
    return diagnostics.index[mask].tolist(), diagnostics


def _same_candidate_group(a: str, b: str, universe: pd.DataFrame, scope: str) -> bool:
    if scope == "all":
        return True
    if scope == "asset_type":
        return universe.loc[a, "asset_type"] == universe.loc[b, "asset_type"]
    if scope == "group":
        return universe.loc[a, "group"] == universe.loc[b, "group"]
    raise ValueError("candidate_scope must be one of: group, asset_type, all")


def _rolling_stability(y: np.ndarray, x: np.ndarray, cfg: ScannerConfig) -> tuple[float, float]:
    window = cfg.rolling_stability_window
    passes, hedges = [], []
    for end in range(window, len(y) + 1, cfg.rolling_stability_step):
        _, hedge, spread = cointegrating_regression(y[end - window : end], x[end - window : end])
        if hedge > 0:
            hedges.append(hedge)
            stat, _, critical_5pct = cointegration_test(
                y[end - window : end], x[end - window : end], cfg.adf_lags, cfg.require_exact_coint
            )
            passes.append(stat <= critical_5pct)
    if not passes:
        return 0.0, float("inf")
    pass_rate = float(np.mean(passes))
    hedge_cv = float(np.std(hedges, ddof=1) / abs(np.mean(hedges))) if len(hedges) > 1 else 0.0
    return pass_rate, hedge_cv


def _current_setup(y: np.ndarray, x: np.ndarray, cfg: ScannerConfig) -> tuple[float, str]:
    y = y[-cfg.regression_lookback :]
    x = x[-cfg.regression_lookback :]
    _, hedge, spread = cointegrating_regression(y, x)
    recent = spread[-cfg.zscore_lookback :]
    sd = float(np.std(recent, ddof=1))
    z = float((spread[-1] - recent.mean()) / sd) if sd > 0 else 0.0
    if cfg.entry_z <= z < cfg.stop_z:
        signal = "SHORT_FIRST_LONG_SECOND"
    elif -cfg.stop_z < z <= -cfg.entry_z:
        signal = "LONG_FIRST_SHORT_SECOND"
    elif abs(z) >= cfg.stop_z:
        signal = "AVOID_EXTREME"
    else:
        signal = "WAIT"
    return z, signal


def _score(row: pd.Series, cfg: ScannerConfig) -> float:
    coint = np.clip((-row.adf_stat - 3.0) / 2.0, 0, 1)
    corr = np.clip((row.return_correlation - cfg.min_return_correlation) / (1 - cfg.min_return_correlation), 0, 1)
    half = math.exp(-abs(math.log(max(row.half_life, 0.1) / 10.0)))
    stability = np.clip(row.stability_pass_rate, 0, 1) * math.exp(-min(row.hedge_ratio_cv, 2.0))
    oos = np.clip((row.oos_sharpe + 0.5) / 2.5, 0, 1)
    drawdown = np.clip(1.0 - abs(row.oos_max_drawdown) / 0.20, 0, 1)
    liquidity = np.clip(math.log10(max(row.min_avg_dollar_volume, 1)) / 10.0, 0, 1)
    return float(100 * (0.24 * coint + 0.17 * stability + 0.14 * corr + 0.12 * half + 0.18 * oos + 0.08 * drawdown + 0.07 * liquidity))


def scan_pairs(
    prices: pd.DataFrame, universe: pd.DataFrame, cfg: ScannerConfig | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return ranked pairs and symbol-level eligibility diagnostics."""
    cfg = cfg or ScannerConfig()
    close, volume = aligned_matrices(prices)
    eligible, diagnostics = _eligible_symbols(close, volume, universe, cfg)

    candidates: list[tuple[float, str, str]] = []
    for a, b in combinations(eligible, 2):
        if not _same_candidate_group(a, b, universe, cfg.candidate_scope):
            continue
        aligned = close[[a, b]].dropna().tail(max(cfg.min_history_days, cfg.formation_days + cfg.validation_days))
        if len(aligned) < cfg.min_history_days:
            continue
        corr = float(np.log(aligned).diff().tail(cfg.correlation_lookback).corr().iloc[0, 1])
        if np.isfinite(corr) and corr >= cfg.min_return_correlation:
            candidates.append((corr, a, b))
    candidates = sorted(candidates, reverse=True)[: cfg.max_candidates]
    candidate_count = len(candidates)

    rows: list[dict] = []
    for correlation, a, b in candidates:
        aligned = close[[a, b]].dropna().tail(cfg.formation_days + cfg.validation_days)
        logs = np.log(aligned.to_numpy(dtype=float))
        formation_end = max(len(logs) - cfg.validation_days, cfg.formation_days)
        formation = logs[max(0, formation_end - cfg.formation_days) : formation_end]
        alpha, hedge, spread = cointegrating_regression(formation[:, 0], formation[:, 1])
        adf, pvalue, critical_5pct = cointegration_test(
            formation[:, 0], formation[:, 1], cfg.adf_lags, cfg.require_exact_coint
        )
        hl = half_life(spread)
        stability_rate, hedge_cv = _rolling_stability(logs[:, 0], logs[:, 1], cfg)
        current_start = max(0, len(logs) - cfg.regression_lookback)
        _, current_coint_pvalue, _ = cointegration_test(
            logs[current_start:, 0], logs[current_start:, 1], cfg.adf_lags, cfg.require_exact_coint
        )
        zscore, signal = _current_setup(logs[:, 0], logs[:, 1], cfg)
        validation_start = max(0, len(logs) - cfg.validation_days - cfg.regression_lookback)
        bt = walk_forward_backtest(logs[validation_start:, 0], logs[validation_start:, 1], cfg)
        rows.append(
            {
                "first_symbol": a,
                "second_symbol": b,
                "first_name": universe.loc[a, "name"],
                "second_name": universe.loc[b, "name"],
                "asset_pair": f"{universe.loc[a, 'asset_type']}/{universe.loc[b, 'asset_type']}",
                "group": universe.loc[a, "group"],
                "eligible_symbols": len(eligible),
                "candidate_pairs_tested": candidate_count,
                "observations": len(logs),
                "return_correlation": correlation,
                "intercept": alpha,
                "hedge_ratio": hedge,
                "adf_stat": adf,
                "coint_critical_5pct": critical_5pct,
                "coint_pvalue": pvalue,
                "current_coint_pvalue": current_coint_pvalue,
                "half_life": hl,
                "hurst": hurst_exponent(spread),
                "zero_crossing_rate": zero_crossing_rate(spread),
                "stability_pass_rate": stability_rate,
                "hedge_ratio_cv": hedge_cv,
                "current_zscore": zscore,
                "setup": signal,
                "oos_sharpe": bt.sharpe,
                "oos_annual_return": bt.annual_return,
                "oos_max_drawdown": bt.max_drawdown,
                "oos_total_return": bt.total_return,
                "oos_trades": bt.trades,
                "oos_win_rate": bt.win_rate,
                "oos_time_in_market": bt.time_in_market,
                "min_avg_dollar_volume": min(
                    diagnostics.loc[a, "avg_dollar_volume"], diagnostics.loc[b, "avg_dollar_volume"]
                ),
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result, diagnostics
    result["fdr_qvalue"] = benjamini_hochberg(result.coint_pvalue.to_numpy())
    result["passes_statistical_filters"] = (
        (result.coint_pvalue <= cfg.max_coint_pvalue)
        & (result.current_coint_pvalue <= cfg.max_coint_pvalue)
        & (result.fdr_qvalue <= cfg.max_fdr_qvalue)
        & result.hedge_ratio.between(cfg.min_hedge_ratio, cfg.max_hedge_ratio)
        & result.half_life.between(cfg.min_half_life, cfg.max_half_life)
        & (result.stability_pass_rate >= cfg.min_stability_pass_rate)
    )
    result["passes_economic_filters"] = (
        (result.oos_sharpe >= cfg.min_oos_sharpe)
        & (result.oos_trades >= cfg.min_oos_trades)
        & (result.oos_win_rate >= cfg.min_oos_win_rate)
        & (result.oos_max_drawdown >= -cfg.max_oos_drawdown)
    )
    result["passes_default_filters"] = (
        result.passes_statistical_filters & result.passes_economic_filters
    )
    result["qualified_setup"] = result.passes_default_filters & result.setup.isin(
        ["LONG_FIRST_SHORT_SECOND", "SHORT_FIRST_LONG_SECOND"]
    )
    result["score"] = result.apply(lambda row: _score(row, cfg), axis=1)
    result = result.sort_values(
        ["passes_default_filters", "passes_statistical_filters", "score", "current_zscore"],
        ascending=[False, False, False, False]
    )
    return result.reset_index(drop=True), diagnostics
