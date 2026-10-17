from __future__ import annotations

import html
from pathlib import Path
import numpy as np
import pandas as pd

from .backtest import walk_forward_backtest
from .config import ScannerConfig
from .data import aligned_matrices
from .statistics import cointegrating_regression, cointegration_test


def _rolling_diagnostics(y: np.ndarray, x: np.ndarray, cfg: ScannerConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(y)
    hedges = np.full(n, np.nan)
    pvalues = np.full(n, np.nan)
    zscores = np.full(n, np.nan)
    start = max(cfg.regression_lookback, cfg.zscore_lookback)
    for t in range(start, n):
        begin = t - cfg.regression_lookback
        _, hedge, spread = cointegrating_regression(y[begin:t], x[begin:t])
        hedges[t] = hedge
        recent = spread[-cfg.zscore_lookback :]
        sd = float(np.std(recent, ddof=1))
        current = y[t] - (y[begin:t].mean() - hedge * x[begin:t].mean()) - hedge * x[t]
        zscores[t] = (current - recent.mean()) / sd if sd > 0 else 0.0
        if t % 21 == 0:
            _, pvalue, _ = cointegration_test(
                y[begin:t], x[begin:t], cfg.adf_lags, cfg.require_exact_coint
            )
            pvalues[t] = pvalue
    return hedges, pd.Series(pvalues).ffill().to_numpy(), zscores


def write_tearsheets(
    ranked: pd.DataFrame,
    prices: pd.DataFrame,
    output_dir: str | Path,
    cfg: ScannerConfig,
) -> list[Path]:
    if ranked.empty or cfg.tear_sheet_count <= 0:
        return []
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(output_dir) / "tear_sheets"
    out.mkdir(parents=True, exist_ok=True)
    close, _ = aligned_matrices(prices)
    written: list[Path] = []
    cards = []
    finalists = ranked.head(cfg.tear_sheet_count)
    for row in finalists.itertuples(index=False):
        a, b = row.first_symbol, row.second_symbol
        aligned = close[[a, b]].dropna().tail(cfg.formation_days + cfg.validation_days)
        dates = aligned.index
        logs = np.log(aligned.to_numpy(dtype=float))
        hedge, pvalue, zscore = _rolling_diagnostics(logs[:, 0], logs[:, 1], cfg)
        bt = walk_forward_backtest(logs[:, 0], logs[:, 1], cfg)
        equity = np.cumprod(1.0 + bt.daily_returns)

        fig, axes = plt.subplots(4, 1, figsize=(12, 12), sharex=True, constrained_layout=True)
        normalized = aligned / aligned.iloc[0] * 100.0
        axes[0].plot(dates, normalized[a], label=a, linewidth=1.3)
        axes[0].plot(dates, normalized[b], label=b, linewidth=1.3)
        axes[0].set_ylabel("Normalized price")
        axes[0].legend(loc="upper left", ncol=2)

        axes[1].plot(dates, zscore, color="#274c77", linewidth=1.0)
        for level, color, style in [(cfg.entry_z, "#d97706", "--"), (-cfg.entry_z, "#d97706", "--"), (0, "#64748b", ":"), (cfg.stop_z, "#b91c1c", ":"), (-cfg.stop_z, "#b91c1c", ":")]:
            axes[1].axhline(level, color=color, linestyle=style, linewidth=0.9)
        axes[1].set_ylabel("Rolling z-score")

        axes[2].plot(dates, hedge, color="#166534", label="hedge ratio", linewidth=1.0)
        axes[2].set_ylabel("Hedge ratio")
        paxis = axes[2].twinx()
        paxis.plot(dates, pvalue, color="#7e22ce", alpha=0.7, label="coint p-value", linewidth=1.0)
        paxis.axhline(cfg.max_coint_pvalue, color="#b91c1c", linestyle="--", linewidth=0.8)
        paxis.set_ylabel("MacKinnon p-value")
        paxis.set_ylim(0, min(1.0, max(0.15, np.nanmax(pvalue) * 1.1 if np.isfinite(pvalue).any() else 0.15)))

        axes[3].plot(dates, equity, color="#0f766e", linewidth=1.2)
        axes[3].axhline(1.0, color="#64748b", linestyle=":", linewidth=0.8)
        axes[3].set_ylabel("Walk-forward equity")
        axes[3].set_xlabel("Date")
        status = "QUALIFIED" if row.passes_default_filters else "RESEARCH ONLY"
        fig.suptitle(
            f"{a} / {b} — {status}\nScore {row.score:.1f} | z {row.current_zscore:.2f} | "
            f"half-life {row.half_life:.1f}d | q {row.fdr_qvalue:.3f} | OOS Sharpe {row.oos_sharpe:.2f}",
            fontsize=13,
        )
        filename = f"{a}_{b}.png".replace("/", "-")
        path = out / filename
        fig.savefig(path, dpi=145)
        plt.close(fig)
        written.append(path)
        cards.append(
            f'<article><h2>{html.escape(a)} / {html.escape(b)}</h2><p>{status} · '
            f'score {row.score:.1f} · setup {html.escape(str(row.setup))}</p><img src="{html.escape(filename)}" alt="{html.escape(a)} and {html.escape(b)} tear sheet"></article>'
        )
    index = out / "index.html"
    index.write_text(
        "<!doctype html><meta charset='utf-8'><title>Pair finalist tear sheets</title>"
        "<style>body{font:14px system-ui;margin:2rem;background:#f4f6f8;color:#17202a}article{background:white;padding:1rem;margin:1.5rem 0;border-radius:10px}img{width:100%;max-width:1200px;height:auto}</style>"
        "<h1>Pair finalist tear sheets</h1><p>Research diagnostics, not trade recommendations.</p>" + "".join(cards)
    )
    written.append(index)
    return written

