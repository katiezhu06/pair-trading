from __future__ import annotations

import html
from pathlib import Path
import numpy as np
import pandas as pd

from .backtest import build_walk_forward_features, simulate_strategy
from .config import ScannerConfig
from .data import aligned_matrices


SCENARIOS = {
    "base": {},
    "entry_1_5": {"entry_z": 1.5},
    "entry_2_5": {"entry_z": 2.5},
    "exit_zero": {"exit_z": 0.0},
    "hold_40": {"max_holding_days": 40},
    "cost_12_5bps": {"one_way_cost_bps": 12.5},
}


def _fold_metrics(returns: np.ndarray, start: int, folds: int, annualization: int) -> tuple[list[float], list[float]]:
    active_indices = np.arange(start, len(returns))
    total_returns, sharpes = [], []
    for indices in np.array_split(active_indices, folds):
        values = returns[indices]
        curve = np.cumprod(1.0 + values)
        total_returns.append(float(curve[-1] - 1.0) if len(curve) else 0.0)
        sd = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        sharpes.append(float(np.mean(values) / sd * np.sqrt(annualization)) if sd > 0 else 0.0)
    return total_returns, sharpes


def evaluate_consistency(
    ranked: pd.DataFrame,
    prices: pd.DataFrame,
    cfg: ScannerConfig,
    folds: int = 4,
) -> tuple[pd.DataFrame, dict[str, dict[str, np.ndarray]]]:
    close, _ = aligned_matrices(prices)
    rows = []
    curves: dict[str, dict[str, np.ndarray]] = {}
    for candidate in ranked.itertuples(index=False):
        a, b = candidate.first_symbol, candidate.second_symbol
        aligned = close[[a, b]].dropna()
        logs = np.log(aligned.to_numpy(dtype=float))
        features = build_walk_forward_features(logs[:, 0], logs[:, 1], cfg)
        results = {name: simulate_strategy(features, cfg, **overrides) for name, overrides in SCENARIOS.items()}
        base = results["base"]
        fold_returns, fold_sharpes = _fold_metrics(
            base.daily_returns, features.start, folds, cfg.annualization
        )
        scenario_returns = {name: result.total_return for name, result in results.items()}
        positive_scenarios = sum(value > 0 for value in scenario_returns.values())
        positive_folds = sum(value > 0 for value in fold_returns)
        positive_curve = base.total_return > 0
        consistent = (
            positive_curve
            and base.sharpe >= cfg.min_oos_sharpe
            and base.trades >= 12
            and base.win_rate >= 0.50
            and base.max_drawdown >= -cfg.max_oos_drawdown
            and positive_folds >= max(3, folds - 1)
            and positive_scenarios >= len(SCENARIOS) - 1
        )
        robustness_score = float(
            12 * positive_folds
            + 6 * positive_scenarios
            + 8 * np.clip(base.sharpe, -2, 3)
            + 10 * np.clip(base.total_return, -0.5, 1.0)
            + 5 * np.clip(base.win_rate if np.isfinite(base.win_rate) else 0, 0, 1)
        )
        row = {
            "first_symbol": a,
            "second_symbol": b,
            "group": candidate.group,
            "scanner_score": candidate.score,
            "scanner_statistical_pass": candidate.passes_statistical_filters,
            "formation_coint_pvalue": candidate.coint_pvalue,
            "current_coint_pvalue": candidate.current_coint_pvalue,
            "fdr_qvalue": candidate.fdr_qvalue,
            "half_life": candidate.half_life,
            "stability_pass_rate": candidate.stability_pass_rate,
            "current_zscore": candidate.current_zscore,
            "current_setup": candidate.setup,
            "full_history_days": len(logs),
            "base_total_return": base.total_return,
            "base_annual_return": base.annual_return,
            "base_sharpe": base.sharpe,
            "base_max_drawdown": base.max_drawdown,
            "base_trades": base.trades,
            "base_win_rate": base.win_rate,
            "positive_folds": positive_folds,
            "positive_scenarios": positive_scenarios,
            "positive_base_curve": positive_curve,
            "consistently_profitable": consistent,
            "robustness_score": robustness_score,
        }
        for index, (fold_return, fold_sharpe) in enumerate(zip(fold_returns, fold_sharpes), 1):
            row[f"fold_{index}_return"] = fold_return
            row[f"fold_{index}_sharpe"] = fold_sharpe
        for name, result in results.items():
            row[f"{name}_total_return"] = result.total_return
            row[f"{name}_sharpe"] = result.sharpe
        rows.append(row)
        if positive_curve:
            curves[f"{a}_{b}"] = {
                name: np.cumprod(1.0 + result.daily_returns) for name, result in results.items()
            } | {"dates": aligned.index.to_numpy()}
    result = pd.DataFrame(rows).sort_values(
        ["consistently_profitable", "positive_base_curve", "positive_folds", "positive_scenarios", "robustness_score"],
        ascending=[False, False, False, False, False],
    )
    return result.reset_index(drop=True), curves


def write_consistency_report(
    result: pd.DataFrame,
    curves: dict[str, dict[str, np.ndarray]],
    output_dir: str | Path,
    top_charts: int = 12,
) -> dict[str, Path]:
    out = Path(output_dir)
    charts = out / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    csv_path = out / "all_pair_consistency.csv"
    positive_path = out / "positive_walk_forward_pairs.csv"
    consistent_path = out / "consistently_profitable_pairs.csv"
    html_path = out / "consistency_report.html"
    result.to_csv(csv_path, index=False)
    positive = result[result.positive_base_curve]
    consistent = result[result.consistently_profitable]
    overlap = consistent[consistent.scanner_statistical_pass]
    positive.to_csv(positive_path, index=False)
    consistent.to_csv(consistent_path, index=False)

    chart_files: dict[str, str] = {}
    if curves and top_charts > 0:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        for row in positive.head(top_charts).itertuples(index=False):
            key = f"{row.first_symbol}_{row.second_symbol}"
            series = curves[key]
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), constrained_layout=True)
            for name in SCENARIOS:
                ax1.plot(series["dates"], series[name], label=name.replace("_", " "), linewidth=1.0)
            ax1.axhline(1.0, color="#64748b", linestyle=":")
            ax1.set_ylabel("Walk-forward equity")
            ax1.legend(ncol=3, fontsize=8)
            fold_values = [getattr(row, f"fold_{i}_return") for i in range(1, 5)]
            colors = ["#15803d" if value > 0 else "#b91c1c" for value in fold_values]
            ax2.bar([f"Fold {i}" for i in range(1, 5)], fold_values, color=colors)
            ax2.axhline(0, color="#64748b", linewidth=0.8)
            ax2.set_ylabel("Base-strategy return")
            fig.suptitle(
                f"{row.first_symbol} / {row.second_symbol} — base {row.base_total_return:.1%}, "
                f"Sharpe {row.base_sharpe:.2f}, {row.positive_folds}/4 positive folds"
            )
            filename = f"{key}.png"
            fig.savefig(charts / filename, dpi=140)
            plt.close(fig)
            chart_files[key] = f"charts/{filename}"

    display_columns = [
        "first_symbol", "second_symbol", "group", "consistently_profitable",
        "base_total_return", "base_sharpe", "base_max_drawdown", "base_trades",
        "base_win_rate", "positive_folds", "positive_scenarios",
        "scanner_statistical_pass", "current_coint_pvalue", "fdr_qvalue",
        "stability_pass_rate", "current_zscore", "robustness_score",
    ]
    shown = positive.head(50)[display_columns].copy()
    formatters = {
        "base_total_return": lambda x: f"{x:.1%}",
        "base_sharpe": lambda x: f"{x:.2f}",
        "base_max_drawdown": lambda x: f"{x:.1%}",
        "base_win_rate": lambda x: f"{x:.0%}",
        "current_coint_pvalue": lambda x: f"{x:.3f}",
        "fdr_qvalue": lambda x: f"{x:.3f}",
        "stability_pass_rate": lambda x: f"{x:.0%}",
        "current_zscore": lambda x: f"{x:.2f}",
        "robustness_score": lambda x: f"{x:.1f}",
    }
    table = shown.to_html(index=False, escape=True, formatters=formatters, classes="ranked")
    cards = []
    for row in positive.head(top_charts).itertuples(index=False):
        key = f"{row.first_symbol}_{row.second_symbol}"
        if key in chart_files:
            cards.append(
                f'<article><h2>{html.escape(row.first_symbol)} / {html.escape(row.second_symbol)}</h2>'
                f'<img src="{chart_files[key]}" alt="robustness chart"></article>'
            )
    html_path.write_text(
        "<!doctype html><meta charset='utf-8'><title>Walk-forward consistency report</title>"
        "<style>body{font:14px system-ui;margin:2rem;background:#f4f6f8;color:#17202a}.cards{display:flex;gap:1rem}.card,article{background:white;padding:1rem;border-radius:10px;margin:1rem 0}.value{font-size:1.8rem;font-weight:700}table{border-collapse:collapse;background:white;width:100%;font-size:12px}th,td{padding:.5rem;border-bottom:1px solid #ddd;text-align:right}th{background:#e8eef5}img{width:100%;max-width:1100px}</style>"
        f"<h1>Walk-forward consistency across all candidate pairs</h1><div class='cards'>"
        f"<div class='card'><div class='value'>{len(result)}</div>pairs tested</div>"
        f"<div class='card'><div class='value'>{len(positive)}</div>positive base curves</div>"
        f"<div class='card'><div class='value'>{len(consistent)}</div>pass profit-consistency rules</div>"
        f"<div class='card'><div class='value'>{len(overlap)}</div>also pass statistical screen</div></div>"
        "<p>Profit consistency requires positive base performance, Sharpe ≥ 0.5, at least 12 trades, win rate ≥ 50%, drawdown ≤ 15%, at least 3/4 positive sequential folds, and at least 5/6 profitable parameter/cost scenarios. This is an exploratory backtest classification; the separate statistical screen enforces the project's cointegration and stability requirements.</p>"
        + table + "".join(cards)
    )
    return {"all_csv": csv_path, "positive_csv": positive_path, "consistent_csv": consistent_path, "html": html_path}
