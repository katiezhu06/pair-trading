# Daily pairs scanner

This is a reusable research scanner for liquid US stocks and ETFs. It ranks
candidate pairs using liquidity, return correlation, Engle–Granger residual
stationarity, mean-reversion speed, rolling parameter stability, multiple-test
control, and a cost-adjusted walk-forward simulation.

It is a research tool, not an automated trading system. It does not connect to
an account, place orders, or assume that an instrument is currently borrowable.

## Data contract

Prices are a long-form CSV:

```text
date,symbol,close,volume
2023-01-03,XOM,103.42,15123456
2023-01-03,CVX,171.44,8234567
```

`close` must be split- and dividend-adjusted. Unadjusted corporate actions can
look like profitable mean reversion and invalidate the result. Each symbol
should have at least 756 common trading days under the defaults.

The universe is a CSV with:

```text
symbol,name,asset_type,group,shortable
XOM,Exxon Mobil,STK,Integrated Oil,true
CVX,Chevron,STK,Integrated Oil,true
```

`group` controls candidate generation by default. Keep groups economically
coherent: industry peers for stocks, or the same exposure/index for ETFs. Use
`candidate_scope: "asset_type"` or `"all"` in a config override for broader
searches, understanding that this greatly increases multiple-testing risk.

## Run

Use the project-local environment, which includes NumPy, pandas, Statsmodels,
SciPy, and Matplotlib:

```bash
PY=.venv-pairs/bin/python
"$PY" -m pairs_scanner universe --output data/universe.csv
"$PY" -m pairs_scanner demo --output reports/demo
"$PY" -m pairs_scanner download \
  --universe data/universe.csv \
  --output data/daily_adjusted_broad.csv \
  --years 5
"$PY" -m pairs_scanner scan \
  --prices data/daily_adjusted_broad.csv \
  --universe data/universe.csv \
  --config config.default.json \
  --output reports/broad_market
"$PY" -m pairs_scanner consistency \
  --prices data/daily_adjusted_broad.csv \
  --ranked reports/broad_market/ranked_pairs_all.csv \
  --config config.default.json \
  --output reports/broad_market/consistency
```

The optional downloader uses Yahoo's public chart endpoint and adjusted-close
series. Provider availability and terms can change; keep the CSV interface as
the stable boundary. IBKR data can be transformed into the same schema for
targeted validation.

The scanner writes:

- `ranked_pairs.html` — readable ranked dashboard
- `ranked_pairs.csv` — top-ranked machine-readable results
- `ranked_pairs_all.csv` — every correlation-screened candidate pair
- `universe_diagnostics.csv` — history, liquidity, and eligibility inputs
- `effective_config.json` — exact settings used
- `tear_sheets/index.html` — charts for the highest-ranked finalists
- `consistency/consistency_report.html` — full-history fold and stress analysis
- `consistency/positive_walk_forward_pairs.csv` — every positive base curve
- `consistency/consistently_profitable_pairs.csv` — pairs passing the profit-consistency rules

The generated stock universe is today's S&P 500 membership, not historical
point-in-time membership. Consequently, the current broad report has
survivorship bias and is suitable for discovery and forward monitoring, not a
claim of historically investable portfolio performance.

## Reading the ranking

The modeled spread is:

```text
log(FIRST) - intercept - hedge_ratio * log(SECOND)
```

`LONG_FIRST_SHORT_SECOND` means the spread is below its fitted equilibrium;
`SHORT_FIRST_LONG_SECOND` means it is above. `WAIT` means there is no entry at
the current close. `AVOID_EXTREME` means the spread is beyond the stop boundary,
where structural-break risk is elevated.

`qualified_setup` is true only when the pair both passes every default filter
and currently has an entry signal. A raw `setup` on a rejected pair is shown
for diagnostic transparency and is not a candidate trade.

`passes_statistical_filters` requires, among other checks, an exact MacKinnon
cointegration p-value <= 0.05, Benjamini–Hochberg false-discovery q-value <=
0.10, acceptable half-life, positive hedge ratio, and at least a 50% pass rate
across rolling cointegration windows. The most recent 252-day MacKinnon p-value
must also be <= 0.05, preventing stale relationships from qualifying.
`passes_economic_filters` additionally
requires cost-adjusted out-of-sample Sharpe >= 0.5, at least five closed trades,
win rate >= 40%, and drawdown no worse than 15%. `passes_default_filters`
requires both. Finalist tear sheets include normalized
prices, rolling z-scores, hedge ratios, cointegration p-values, and walk-forward
equity. A longer point-in-time dataset is still required before committing capital.

The out-of-sample fields use a rolling regression, one-close signal delay,
gross-normalized hedge exposure, a 20-day maximum hold, and 7.5 bps one-way
turnover costs by default. They do not model borrow recalls, locate fees,
dividend payments on shorts, taxes, market impact, or partial fills.

The consistency analysis uses the full available history after a 252-day
rolling warm-up. It reports four sequential folds and six variants: the base
strategy, entry z-scores of 1.5 and 2.5, zero-crossing exits, a 40-day maximum
hold, and 12.5 bps one-way costs. Profit consistency requires a positive base
curve, Sharpe >= 0.5, at least 12 completed trades, win rate >= 50%, drawdown
no worse than 15%, at least three positive folds, and at least five profitable
variants. This classification remains exploratory unless the separate
cointegration and stability filters also pass.

## Research workflow

1. Maintain an economically grouped, point-in-time universe.
2. Refresh adjusted daily bars after the close.
3. Run the scanner and inspect only pairs passing the default filters.
4. Review spread charts, news/corporate actions, borrow status, and live bid/ask
   spreads.
5. Size both legs from the current hedge ratio and risk budget.
6. If desired, use IBKR to create reviewable instructions only after confirming
   live quantities and limit prices.
