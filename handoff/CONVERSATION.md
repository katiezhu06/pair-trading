# Project Conversation Record

This is the human/assistant project dialogue, reconstructed from the Codex task
record `019fb520-519b-73c2-b209-dac057cd0116`. Tool logs and hidden chain-of-
thought are intentionally excluded; substantive user requests, decisions,
progress explanations, and delivered results are retained.

## 1. Project objective

**User**

> The goal of this project is to research and trade pairs of stocks, stock vs
> ETF, ETF vs ETF or futures against one another. The pair should be highly
> liquid, strongly co-integrated and the delta between the pair should show
> strong mean-reverting behavior. I want to be able to spot good pair trading
> setups that I can then trade in my IBKR account. If you need further
> information, please ask for as much detail as you like.

**Assistant**

Inspected the existing project and confirmed that the IBKR connector supported
contract lookup, historical/live prices, watchlists, account data, and
reviewable order instructions. Found an older MATLAB pairs-trading codebase and
recommended preserving it while building a clean Python research pipeline.
Proposed defaults: daily US stocks/ETFs first; 2–20 day holds; cointegrating
hedge ratio; entry near ±2 z, exit near zero, stop around ±4; Engle–Granger/ADF,
half-life, Hurst/stability checks, false-discovery control, and cost-aware
walk-forward validation. Explicitly stated that no account access or order
creation would occur without authorization.

## 2. Initial scanner request

**User**

> Let's start with the default settings and just build an initial reusable
> daily-bar scanner for liquid US stocks and ETFs, with the ranked report, as
> you suggest.

**Assistant**

Built a Python module beside the legacy MATLAB files using adjusted daily data,
economic-group candidate generation, liquidity/history filters, cointegration
and mean-reversion diagnostics, walk-forward testing, and CSV/HTML reports.
Implemented a stable CSV data contract and a synthetic test dataset. Added a
Yahoo adjusted-price downloader and verified IBKR contract resolution for a
small 13-symbol universe. Unit and end-to-end tests passed.

The initial real-data report through 2026-07-30 ranked seven peer candidates;
none passed all filters. A raw Visa/Mastercard z-score was elevated but failed
cointegration/stability and was not labeled a qualified setup.

## 3. Recommendation discussion

**User**

> OK, that's a great start! What is your suggested next step?

**Assistant**

Recommended expanding to roughly 300–500 liquid US stocks and 50–100 ETFs,
grouped economically; upgrading to exact MacKinnon cointegration inference;
creating detailed finalist tear sheets; and separating statistical quality,
current opportunity, and expected net profitability. Proposed forward paper
monitoring before any live allocation and deferred futures to a separate phase.

## 4. Broad-market expansion

**User**

> I agree. Let's proceed with steps 1–2.

**Assistant**

Built a refreshable universe of 503 current S&P 500 listings plus 105 curated
unleveraged ETFs in 154 economic groups. Installed project-local Statsmodels,
SciPy, and Matplotlib. Added exact MacKinnon p-values, FDR correction,
current-window cointegration, economic validation filters, and finalist tear
sheets. Downloaded 759,374 adjusted bars through 2026-07-30.

The broad run had 586 eligible instruments and tested 539 pairs. One pair,
IJH/MDY, passed the strict current statistical screen but had poor cost-adjusted
validation, so zero pairs passed both statistical and economic filters. The
assistant emphasized current-membership survivorship bias.

## 5. Full profitability consistency test

**User**

> It is really interesting that all the “walk forward equity” curves all show
> losses. Do any of your 539 pairs show a positive walk forward equity curve?
> Can you test all the pairs and see which ones are consistently profitable?

**Assistant**

Retained all 539 candidates rather than only the displayed top 50. Refactored
the walk-forward engine to compute rolling hedge ratios and z-scores once per
pair, then tested each pair over full available history, four sequential folds,
and six variants: base settings, entry z=1.5, entry z=2.5, exit at zero,
40-day maximum holding period, and 12.5 bps one-way costs.

Results:

- 192/539 had positive base walk-forward curves.
- 114 were profitable in at least 3/4 folds.
- 14 were profitable in all 4 folds.
- 92 remained profitable in all 6 scenarios.
- 41 passed the full exploratory profit-consistency rules.
- 0 of those 41 also passed the strict current cointegration/stability screen.

Leading examples and base results:

| Pair | Total return | Sharpe | Positive folds | Scenarios |
|---|---:|---:|---:|---:|
| ADSK / PTC | 57.7% | 1.16 | 4/4 | 6/6 |
| ALL / TRV | 35.0% | 1.12 | 4/4 | 6/6 |
| LII / TT | 25.1% | 0.55 | 4/4 | 6/6 |
| LVS / WYNN | 22.6% | 0.62 | 4/4 | 6/6 |
| SRE / XEL | 19.3% | 0.68 | 4/4 | 6/6 |
| ACN / CTSH | 18.1% | 0.63 | 4/4 | 6/6 |
| NI / PNW | 17.1% | 0.77 | 4/4 | 6/6 |
| PNC / TFC | 16.8% | 0.75 | 4/4 | 6/6 |
| AZO / ORLY | 11.7% | 0.53 | 4/4 | 6/6 |
| CPT / MAA | 7.2% | 0.54 | 4/4 | 6/6 |

The assistant recommended freezing a 10–20 pair cohort for genuinely unseen
forward paper monitoring. It cautioned that the 41 are promising research
candidates, not qualified cointegrated trades.

## 6. Handoff request

**User**

> This is great, thanks! Now, I want to bundle up everything we've done in this
> project, and hand it off to one of my students so she can carry on and continue
> the work. Could you please bundle up everything you've done here, in a way that
> she could just open it and use her own AI system to pick up the work where we
> left off? Include all conversations, context, data and code, as well as any
> other relevant resource or material that we can hand off to her, and provide it
> in a convenient format that we can share (maybe a zip file or such?)

**Assistant action**

Created this portable archive with code, tests, configurations, datasets,
reports, relevant legacy MATLAB sources, project context, conversation record,
manifest, and checksums. A public immutable task link was not authorized by the
app, so this archive is the handoff source of truth.

