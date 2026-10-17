from __future__ import annotations

from datetime import datetime, timezone
import html
import json
from pathlib import Path
import pandas as pd

from .config import ScannerConfig


DISPLAY_COLUMNS = [
    "score", "first_symbol", "second_symbol", "asset_pair", "group",
    "passes_default_filters", "passes_statistical_filters", "passes_economic_filters", "qualified_setup", "setup", "current_zscore", "hedge_ratio",
    "return_correlation", "adf_stat", "coint_pvalue", "current_coint_pvalue", "fdr_qvalue",
    "half_life", "hurst", "stability_pass_rate", "hedge_ratio_cv",
    "oos_sharpe", "oos_annual_return", "oos_max_drawdown", "oos_trades",
    "oos_win_rate", "min_avg_dollar_volume",
]


def write_reports(
    ranked: pd.DataFrame,
    diagnostics: pd.DataFrame,
    output_dir: str | Path,
    cfg: ScannerConfig,
    data_as_of: str,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "ranked_pairs.csv"
    all_csv_path = out / "ranked_pairs_all.csv"
    diag_path = out / "universe_diagnostics.csv"
    html_path = out / "ranked_pairs.html"
    config_path = out / "effective_config.json"
    ranked.to_csv(all_csv_path, index=False)
    ranked.head(cfg.top_n).to_csv(csv_path, index=False)
    diagnostics.to_csv(diag_path, index=True)
    config_path.write_text(json.dumps(cfg.to_dict(), indent=2) + "\n")

    if ranked.empty:
        table = "<p>No pairs passed candidate generation. Inspect universe_diagnostics.csv and loosen filters if justified.</p>"
        setups = passes = statistical = tested = 0
    else:
        shown = ranked.head(cfg.top_n)[[c for c in DISPLAY_COLUMNS if c in ranked]].copy()
        format_specs = {
            "score": "{:.1f}", "current_zscore": "{:.2f}", "hedge_ratio": "{:.3f}",
            "return_correlation": "{:.3f}", "adf_stat": "{:.2f}",
            "coint_pvalue": "{:.3f}", "current_coint_pvalue": "{:.3f}", "fdr_qvalue": "{:.3f}", "half_life": "{:.1f}",
            "hurst": "{:.2f}", "stability_pass_rate": "{:.0%}", "hedge_ratio_cv": "{:.2f}",
            "oos_sharpe": "{:.2f}", "oos_annual_return": "{:.1%}",
            "oos_max_drawdown": "{:.1%}", "oos_win_rate": "{:.0%}",
            "min_avg_dollar_volume": "${:,.0f}",
        }
        formatters = {
            column: (lambda value, spec=spec: spec.format(value))
            for column, spec in format_specs.items()
            if column in shown.columns
        }
        table = shown.to_html(index=False, escape=True, formatters=formatters, classes="ranked")
        setups = int(ranked.qualified_setup.sum())
        passes = int(ranked.passes_default_filters.sum())
        statistical = int(ranked.passes_statistical_filters.sum())
        tested = int(ranked.candidate_pairs_tested.iloc[0])

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Daily Pairs Scanner</title>
<style>
body{{font:14px system-ui,-apple-system,sans-serif;margin:2rem;color:#1d2733;background:#f6f8fb}}
h1{{margin-bottom:.2rem}} .meta{{color:#5c6b7a}} .cards{{display:flex;gap:1rem;margin:1.5rem 0;flex-wrap:wrap}}
.card{{background:white;border:1px solid #dfe5ec;border-radius:10px;padding:1rem;min-width:150px}}
.value{{font-size:1.7rem;font-weight:650}} .table-wrap{{overflow:auto;background:white;border-radius:10px;border:1px solid #dfe5ec}}
table{{border-collapse:collapse;width:100%;font-size:12px}} th,td{{padding:.55rem;border-bottom:1px solid #e8edf2;text-align:right;white-space:nowrap}}
th{{background:#edf2f7;position:sticky;top:0}} th:nth-child(2),th:nth-child(3),th:nth-child(4),th:nth-child(5),th:nth-child(7),td:nth-child(2),td:nth-child(3),td:nth-child(4),td:nth-child(5),td:nth-child(7){{text-align:left}}
.note{{max-width:1000px;line-height:1.5;margin-top:1.5rem;color:#475665}}
</style></head><body>
<h1>Daily pairs scanner</h1><div class="meta">Data through {html.escape(data_as_of)} · generated {generated}</div>
<div class="cards"><div class="card"><div class="value">{tested}</div>candidate pairs tested</div><div class="card"><div class="value">{len(ranked)}</div>ranked candidates shown</div>
<div class="card"><div class="value">{statistical}</div>statistical finalists</div><div class="card"><div class="value">{passes}</div>pass statistical + economic</div><div class="card"><div class="value">{setups}</div>qualified setups now</div></div>
<div class="table-wrap">{table}</div>
<p class="note"><strong>Interpretation:</strong> FIRST/SECOND defines the modeled log-price spread. A setup is a research alert, not an order recommendation. Results include Engle–Granger tests with MacKinnon p-values, false-discovery adjustment, rolling stability, and a cost-adjusted walk-forward simulation. Confirm borrow availability, live spreads, corporate actions, and position sizing before trading.</p>
</body></html>"""
    html_path.write_text(html_doc)
    return {"csv": csv_path, "all_csv": all_csv_path, "diagnostics": diag_path, "html": html_path, "config": config_path}
