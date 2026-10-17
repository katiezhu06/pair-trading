# Archive Manifest

## `code/`

- `pairs_scanner/`: complete Python package.
- `tests/`: deterministic unit and integration tests.
- `config.default.json`: research defaults used for the reports.
- `requirements-pairs-scanner.txt`: Python dependencies.
- `universe.example.csv`: small example universe.
- `README_PAIRS_SCANNER.md`: detailed command and methodology documentation.

## `data/`

- `daily_adjusted_broad.csv`: 759,374 adjusted daily observations for the broad
  run, through 2026-07-30.
- `universe.csv`: 608-instrument stock/ETF universe used for the broad run.
- `universe.metadata.json`: provenance and universe counts.
- `daily_adjusted.csv`: small 13-symbol smoke-test dataset.

## `reports/`

- Complete broad-market scan, all-candidate output, universe diagnostics,
  current configuration, tear sheets, consistency tables, and charts.
- Earlier demonstration/smoke reports are included for development history.

## `legacy_matlab/`

- Relevant pre-existing pairs-trading MATLAB functions and scripts.
- `cointegration/`: legacy ADF/CADF helpers and example workbook.
- `matlab_webinar/`: pairs-trading examples and models; the unrelated 49 MB
  Access database is excluded to keep the handoff focused.

The legacy code predates the Python system, uses older data-source assumptions,
and is included for intellectual provenance—not as the recommended execution
path.

## `handoff/`

- `HANDOFF_README.md`: human quick start.
- `AI_CONTEXT.md`: detailed machine-readable continuation brief.
- `CONVERSATION.md`: project dialogue and decision history.
- `MANIFEST.md`: this file.
- `PROJECT_STATE.json`: compact machine-readable project status.
- `VALIDATION.md`: package-level test and data-integrity assertions.
- `checksums.sha256`: integrity hashes for every packaged file except itself.

## Deliberate exclusions

- `.venv-pairs/`: 222 MB machine-specific virtual environment; reproducible
  from `requirements-pairs-scanner.txt`.
- Python `__pycache__`, `.DS_Store`, editor backups, and temporary files.
- Unrelated personal investment documents and unrelated code in the original
  618 MB workspace.
- Brokerage credentials, account data, positions, and orders: none were used or
  created in this project.
