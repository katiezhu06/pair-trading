"""Daily-bar statistical-arbitrage scanner."""

from .config import ScannerConfig
from .scanner import scan_pairs

__all__ = ["ScannerConfig", "scan_pairs"]

