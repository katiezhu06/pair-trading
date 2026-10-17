# Handoff Validation

Validation performed on the copied package on 2026-10-15:

- Python test suite: **4/4 passed**.
- Broad price rows: **759,374**.
- Price range: **2021-07-20 through 2026-07-30**.
- Universe rows: **608**.
- Candidate-pair results: **539**.
- Positive base walk-forward pairs: **192**.
- Profit-consistent pairs: **41**.
- Strict statistical + profit-consistent overlap: **0**.

The copied package was tested by setting `PYTHONPATH=code` and using the
project's source environment. The packaged virtual environment is deliberately
excluded; install `code/requirements-pairs-scanner.txt` in a fresh environment.

