# Pairs-Trading Research Project — Student Handoff

Snapshot prepared: **2026-10-15**  
Market-data snapshot: **through 2026-07-30**  
Original Codex task: `019fb520-519b-73c2-b209-dac057cd0116` (`Build pair trading research`)

This archive contains the complete Python research system developed in the
project, its input data, generated results, tests, relevant predecessor MATLAB
code, an AI-ready project brief, and a transcript of the project conversation.

## Start here

1. Read `AI_CONTEXT.md`. It tells a new human or AI collaborator what was built,
   why decisions were made, the current empirical results, and what remains.
2. Read `CONVERSATION.md` for the original project dialogue and evolution.
3. Create a Python environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   python -m pip install -r requirements-pairs-scanner.txt
   python -m unittest discover -s tests -v
   ```

4. Run the deterministic smoke test:

   ```bash
   python -m pairs_scanner demo --output reports/demo_new
   ```

5. Refresh the universe and prices before drawing current conclusions—the
   bundled bars stop on 2026-07-30:

   ```bash
   python -m pairs_scanner universe --output data/universe_current.csv
   python -m pairs_scanner download \
     --universe data/universe_current.csv \
     --output data/daily_adjusted_current.csv \
     --years 5
   ```

6. Run the broad scan and robustness analysis:

   ```bash
   python -m pairs_scanner scan \
     --prices data/daily_adjusted_current.csv \
     --universe data/universe_current.csv \
     --config config.default.json \
     --output reports/current

   python -m pairs_scanner consistency \
     --prices data/daily_adjusted_current.csv \
     --ranked reports/current/ranked_pairs_all.csv \
     --config config.default.json \
     --output reports/current/consistency
   ```

## Most important bundled results

- `reports/broad_market/ranked_pairs.html` — broad statistical scan dashboard.
- `reports/broad_market/ranked_pairs_all.csv` — all 539 screened candidates.
- `reports/broad_market/tear_sheets/index.html` — finalist diagnostics.
- `reports/broad_market/consistency/consistency_report.html` — full-history
  profitability/robustness analysis.
- `reports/broad_market/consistency/positive_walk_forward_pairs.csv` — 192
  positive base walk-forward curves.
- `reports/broad_market/consistency/consistently_profitable_pairs.csv` — 41
  pairs passing the exploratory profit-consistency rules.

## Critical interpretation

The last completed run found **41 backtest-consistent pairs, but none also
passed the strict current cointegration/stability screen**. Therefore, the
archive contains promising research candidates, not trade recommendations.
The data also uses current S&P 500 membership across historical bars, which
creates survivorship bias.

No IBKR account balances or positions were accessed and no orders or order
instructions were created.

