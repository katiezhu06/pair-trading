# AI Context: Continue the Pairs-Trading Research

You are inheriting a Python research project for identifying liquid US
stock/ETF pairs whose fitted spread is stationary and mean reverting, and whose
strategy remains profitable after costs in walk-forward testing. The eventual
workflow may use Interactive Brokers for live validation and reviewable order
instructions, but execution is deliberately outside the current system.

## Owner's objective

Research stock/stock, stock/ETF, ETF/ETF, and eventually futures pairs. Desired
pairs are highly liquid, strongly cointegrated, exhibit stable mean reversion,
and present actionable spread deviations. The first completed phase focuses on
daily US stocks and ETFs. Futures were explicitly deferred because expiry
selection, rolls, term structure, contract multipliers, and margin require a
separate model.

## Defaults chosen

- Daily adjusted closes; expected holding period 2–20 trading days.
- Current S&P 500 constituents plus curated unleveraged ETFs.
- Candidate generation within GICS sub-industries or matched ETF exposure
  families, preventing an indiscriminate all-to-all search.
- At least 756 daily observations, price >= $5, 60-day average dollar volume >=
  $25 million, and a 252-day return correlation >= 0.60.
- Log-price Engle–Granger regression with intercept and exact MacKinnon
  inference from Statsmodels.
- Benjamini–Hochberg false-discovery correction across tested candidates.
- Formation window 504 days; trailing validation window 252 days; rolling
  regression 252 days; z-score window 60 days.
- Entry at |z| >= 2, exit near |z| <= 0.25, structural stop at |z| >= 4,
  maximum holding period 20 days.
- One-way cost assumption 7.5 bps; gross-normalized hedge exposure.
- Statistical filtering requires formation and current cointegration,
  acceptable half-life, positive hedge ratio, and rolling stability.
- Economic filtering requires OOS Sharpe >= 0.5, at least five trades, win rate
  >= 40%, and maximum drawdown no worse than 15%.

The exact configuration is in `config.default.json` and
`pairs_scanner/config.py`.

## Architecture

- `pairs_scanner/universe.py`: current S&P 500 ingestion and curated ETF groups.
- `pairs_scanner/download.py`: concurrent adjusted Yahoo chart downloads.
- `pairs_scanner/data.py`: validates long-form data and constructs aligned
  close/volume matrices.
- `pairs_scanner/statistics.py`: OLS, ADF support, exact Engle–Granger/MacKinnon
  test, half-life, Hurst exponent, zero crossings, and FDR correction.
- `pairs_scanner/scanner.py`: liquidity/history screening, candidate generation,
  formation/current statistical tests, scoring, and trailing walk-forward
  economics.
- `pairs_scanner/backtest.py`: no-look-ahead rolling hedge/z-score features and
  execution simulation.
- `pairs_scanner/consistency.py`: full-history four-fold and six-scenario
  robustness analysis.
- `pairs_scanner/report.py`: ranked CSV/HTML reporting.
- `pairs_scanner/tearsheet.py`: visual finalist diagnostics.
- `pairs_scanner/__main__.py`: CLI.
- `tests/test_pairs_scanner.py`: deterministic regression tests.

## Data contract

Price CSV columns: `date,symbol,close,volume`. `close` must be split- and
dividend-adjusted. Universe columns:
`symbol,name,asset_type,group,broad_group,shortable,source`.

The stable interface is the CSV schema; the provider can be replaced. The
bundled Yahoo data is for research and reproducibility. For any proposed trade,
validate current prices, spreads, borrow, contract identity, and corporate
actions through IBKR or another institutional source.

## Completed empirical results

Broad run using data through 2026-07-30:

- Universe: 503 current S&P 500 listings + 105 ETFs = 608 instruments.
- 586 passed basic eligibility.
- 539 within-group, correlation-screened pairs were tested.
- Only IJH/MDY passed the final current statistical filters in the initial broad
  ranking, but its cost-adjusted validation was strongly negative, so no pair
  passed both statistical and economic filters.

Full-history consistency test across all 539 pairs:

- 192 had a positive base walk-forward equity curve.
- 114 were positive in at least 3 of 4 sequential folds.
- 14 were positive in all 4 folds.
- 92 were positive in all 6 parameter/cost scenarios.
- 41 met the exploratory profit-consistency definition.
- 0 of those 41 also passed the strict current statistical screen.

Leading profit-consistent examples were ADSK/PTC, ALL/TRV, NI/PNW, PNC/TFC,
SRE/XEL, LVS/WYNN, LII/TT, ACN/CTSH, AZO/ORLY, and CPT/MAA. These must not be
called qualified cointegrated trades: most fail current cointegration, FDR, or
rolling-stability requirements.

## Why top statistical pairs lost money

Many near-substitute ETFs have extremely strong stationarity but sub-two-day
half-lives. At daily frequency, small deviations are overwhelmed by modeled
turnover costs. Conversely, several profitable backtests appear to exploit
temporary/regime-dependent relationships rather than stable cointegration.
This tension is a key research finding, not a software error.

## Known limitations

1. Survivorship bias: current S&P 500 membership is used historically.
2. Selection bias: the same dataset generated and evaluated candidates.
3. Only about five years of downloaded bars were used.
4. Yahoo is not an execution-grade or guaranteed data source.
5. Short borrow cost/availability, dividend liability, market impact, taxes,
   partial fills, and live bid/ask spreads are not modeled.
6. Corporate-event and structural-break handling can be improved.
7. Full-history folds are sequential diagnostics, not a nested research design
   with an untouched final holdout.
8. “shortable” in the universe is only a placeholder.
9. Portfolio-level overlap, beta/factor exposure, and capital allocation are not
   yet modeled.
10. No automated brokerage action exists.

## Recommended next work

Highest priority:

1. Freeze a forward-monitoring cohort of 10–20 candidates before refreshing
   data; record daily signals and hypothetical fills without revising rules.
2. Obtain point-in-time constituents (or a survivorship-free universe) and
   longer histories, then repeat with nested walk-forward selection/evaluation.
3. Add pair-specific break detection, parameter drift alerts, and explicit
   “eligible / watch / invalidated” state transitions.
4. Add live spread/borrow validation via IBKR for research finalists.
5. Model short dividends, borrow fees, bid/ask spreads, and market impact.
6. Build portfolio construction with shared-leg, sector, beta, and gross/net
   exposure limits.

Do not loosen cointegration thresholds merely to make historical performance
look better. Treat the zero-overlap result as a hypothesis to investigate:
possibly stable cointegration and profitable daily execution require different
frequencies, signal designs, or a broader relationship model.

## Instructions for another AI system

Before changing behavior:

1. Run the tests and the synthetic demo.
2. Reproduce the bundled broad report from the bundled data.
3. Compare output hashes/counts and explain any dependency-version differences.
4. Preserve no-look-ahead behavior: today's signal changes the position for the
   next close-to-close return; yesterday's position earns today's return.
5. Keep statistical qualification and exploratory profitability labels
   separate.
6. Never place or prepare an IBKR trade without explicit human approval,
   current contract resolution, quantities, and limit prices.

