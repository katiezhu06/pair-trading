from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .config import ScannerConfig


@dataclass
class WalkForwardFeatures:
    pair_returns: np.ndarray
    hedges: np.ndarray
    zscores: np.ndarray
    start: int


@dataclass
class BacktestResult:
    sharpe: float
    annual_return: float
    max_drawdown: float
    trades: int
    win_rate: float
    time_in_market: float
    total_return: float
    daily_returns: np.ndarray
    positions: np.ndarray
    zscores: np.ndarray


def build_walk_forward_features(
    log_y: np.ndarray, log_x: np.ndarray, cfg: ScannerConfig
) -> WalkForwardFeatures:
    """Compute rolling hedge ratios, z-scores, and gross pair returns once."""
    y = np.asarray(log_y, dtype=float)
    x = np.asarray(log_x, dtype=float)
    n = len(y)
    pair_returns = np.zeros(n)
    hedges = np.full(n, np.nan)
    zscores = np.full(n, np.nan)
    start = max(cfg.regression_lookback, cfg.zscore_lookback) + 1
    for t in range(start, n):
        begin = t - cfg.regression_lookback
        xw, yw = x[begin:t], y[begin:t]
        x_centered = xw - xw.mean()
        denominator = float(x_centered @ x_centered)
        if denominator <= 0:
            continue
        hedge = float(x_centered @ (yw - yw.mean()) / denominator)
        if hedge <= 0 or not np.isfinite(hedge):
            continue
        intercept = float(yw.mean() - hedge * xw.mean())
        calibration_spread = yw - intercept - hedge * xw
        recent = calibration_spread[-cfg.zscore_lookback :]
        sd = float(np.std(recent, ddof=1))
        current_spread = y[t] - intercept - hedge * x[t]
        zscores[t] = float((current_spread - recent.mean()) / sd) if sd > 0 else 0.0
        hedges[t] = hedge
        pair_returns[t] = (
            (y[t] - y[t - 1]) - hedge * (x[t] - x[t - 1])
        ) / (1.0 + abs(hedge))
    return WalkForwardFeatures(pair_returns, hedges, zscores, start)


def _summarize(
    returns: np.ndarray,
    positions: np.ndarray,
    zscores: np.ndarray,
    trade_pnls: list[float],
    start: int,
    annualization: int,
) -> BacktestResult:
    active = returns[start:]
    if len(active) == 0:
        return BacktestResult(0, 0, 0, 0, float("nan"), 0, 0, returns, positions, zscores)
    sd = float(np.std(active, ddof=1))
    sharpe = float(np.mean(active) / sd * np.sqrt(annualization)) if sd > 0 else 0.0
    curve = np.cumprod(1.0 + active)
    peaks = np.maximum.accumulate(curve)
    max_dd = float(np.min(curve / peaks - 1.0)) if len(curve) else 0.0
    years = max(len(active) / annualization, 1 / annualization)
    total = float(curve[-1] - 1.0) if len(curve) else 0.0
    annual = float(curve[-1] ** (1.0 / years) - 1.0) if len(curve) and curve[-1] > 0 else -1.0
    wins = float(np.mean(np.asarray(trade_pnls) > 0)) if trade_pnls else float("nan")
    return BacktestResult(
        sharpe=sharpe,
        annual_return=annual,
        max_drawdown=max_dd,
        trades=len(trade_pnls),
        win_rate=wins,
        time_in_market=float(np.mean(positions[start:] != 0)),
        total_return=total,
        daily_returns=returns,
        positions=positions,
        zscores=zscores,
    )


def simulate_strategy(
    features: WalkForwardFeatures,
    cfg: ScannerConfig,
    *,
    entry_z: float | None = None,
    exit_z: float | None = None,
    stop_z: float | None = None,
    max_holding_days: int | None = None,
    one_way_cost_bps: float | None = None,
) -> BacktestResult:
    entry = cfg.entry_z if entry_z is None else entry_z
    exit_level = cfg.exit_z if exit_z is None else exit_z
    stop = cfg.stop_z if stop_z is None else stop_z
    max_hold = cfg.max_holding_days if max_holding_days is None else max_holding_days
    cost_bps = cfg.one_way_cost_bps if one_way_cost_bps is None else one_way_cost_bps
    n = len(features.zscores)
    returns = np.zeros(n)
    positions = np.zeros(n)
    position = 0
    age = 0
    equity = 1.0
    entry_equity = 1.0
    trade_pnls: list[float] = []

    for t in range(features.start, n):
        z = features.zscores[t]
        old_position = position
        if not np.isfinite(z):
            position = 0
        elif position == 0:
            if entry <= z < stop:
                position = -1
            elif -stop < z <= -entry:
                position = 1
            if position:
                age = 0
                entry_equity = equity
        else:
            age += 1
            crossed = (position == 1 and z >= -exit_level) or (position == -1 and z <= exit_level)
            stopped = abs(z) >= stop or age >= max_hold
            if crossed or stopped:
                position = 0

        turnover = abs(position - old_position)
        net_return = old_position * features.pair_returns[t] - turnover * cost_bps / 10_000.0
        returns[t] = net_return
        positions[t] = position
        equity *= max(1.0 + net_return, 1e-9)
        if old_position != 0 and position == 0:
            trade_pnls.append(equity / entry_equity - 1.0)

    return _summarize(
        returns, positions, features.zscores.copy(), trade_pnls, features.start, cfg.annualization
    )


def walk_forward_backtest(log_y: np.ndarray, log_x: np.ndarray, cfg: ScannerConfig) -> BacktestResult:
    return simulate_strategy(build_walk_forward_features(log_y, log_x, cfg), cfg)

