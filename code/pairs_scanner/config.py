from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path


@dataclass(frozen=True)
class ScannerConfig:
    """Conservative defaults for daily US stock/ETF pairs."""

    min_history_days: int = 756
    liquidity_lookback: int = 60
    min_avg_dollar_volume: float = 25_000_000.0
    min_price: float = 5.0
    correlation_lookback: int = 252
    min_return_correlation: float = 0.60
    formation_days: int = 504
    validation_days: int = 252
    regression_lookback: int = 252
    zscore_lookback: int = 60
    adf_lags: int = 1
    require_exact_coint: bool = True
    max_coint_pvalue: float = 0.05
    max_fdr_qvalue: float = 0.10
    min_hedge_ratio: float = 0.10
    max_hedge_ratio: float = 10.0
    min_half_life: float = 2.0
    max_half_life: float = 60.0
    rolling_stability_window: int = 252
    rolling_stability_step: int = 63
    min_stability_pass_rate: float = 0.50
    min_oos_sharpe: float = 0.50
    min_oos_trades: int = 5
    min_oos_win_rate: float = 0.40
    max_oos_drawdown: float = 0.15
    entry_z: float = 2.0
    exit_z: float = 0.25
    stop_z: float = 4.0
    max_holding_days: int = 20
    one_way_cost_bps: float = 7.5
    annualization: int = 252
    candidate_scope: str = "group"  # group, asset_type, or all
    max_candidates: int = 5_000
    top_n: int = 50
    tear_sheet_count: int = 10

    @classmethod
    def from_json(cls, path: str | Path | None) -> "ScannerConfig":
        if path is None:
            return cls()
        raw = json.loads(Path(path).read_text())
        allowed = {f.name for f in fields(cls)}
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
        return cls(**raw)

    def to_dict(self) -> dict:
        return asdict(self)
