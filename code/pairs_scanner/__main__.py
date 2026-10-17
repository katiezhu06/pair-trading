from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

from .config import ScannerConfig
from .data import load_prices, load_universe
from .demo import make_demo_data
from .download import download_yahoo_adjusted
from .report import write_reports
from .scanner import scan_pairs
from .universe import build_universe
from .tearsheet import write_tearsheets
from .consistency import evaluate_consistency, write_consistency_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily-bar stock and ETF pairs scanner")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="scan long-form daily price data")
    scan.add_argument("--prices", required=True, help="CSV: date,symbol,close,volume")
    scan.add_argument("--universe", required=True, help="CSV: symbol,name,asset_type,group,shortable")
    scan.add_argument("--config", help="optional JSON overrides")
    scan.add_argument("--output", default="reports/latest")
    demo = sub.add_parser("demo", help="run a deterministic synthetic smoke test")
    demo.add_argument("--output", default="reports/demo")
    download = sub.add_parser("download", help="download adjusted Yahoo daily bars for a universe")
    download.add_argument("--universe", required=True)
    download.add_argument("--output", default="data/daily_adjusted.csv")
    download.add_argument("--years", type=int, default=5)
    universe_cmd = sub.add_parser("universe", help="build current S&P 500 plus curated ETF universe")
    universe_cmd.add_argument("--output", default="data/universe.csv")
    consistency = sub.add_parser("consistency", help="stress-test every ranked candidate across folds and scenarios")
    consistency.add_argument("--prices", required=True)
    consistency.add_argument("--ranked", required=True, help="ranked_pairs_all.csv from a scan")
    consistency.add_argument("--config", help="optional JSON overrides")
    consistency.add_argument("--output", default="reports/consistency")
    args = parser.parse_args()

    if args.command == "universe":
        frame, metadata = build_universe(args.output)
        print(f"Wrote {len(frame)} instruments to {Path(args.output).resolve()}")
        print(f"metadata: {metadata.resolve()}")
        return

    if args.command == "download":
        universe = load_universe(args.universe)
        end = date.today()
        start = end - timedelta(days=365 * args.years + args.years // 4 + 10)
        frame = download_yahoo_adjusted(universe.symbol.tolist(), start, end)
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(destination, index=False)
        print(f"Wrote {len(frame)} adjusted daily bars to {destination.resolve()}")
        return

    if args.command == "consistency":
        cfg = ScannerConfig.from_json(args.config)
        prices = load_prices(args.prices)
        ranked = pd.read_csv(args.ranked)
        result, curves = evaluate_consistency(ranked, prices, cfg)
        paths = write_consistency_report(result, curves, args.output)
        print(f"Tested {len(result)} pairs; {int(result.positive_base_curve.sum())} have positive base curves; {int(result.consistently_profitable.sum())} meet consistency rules.")
        for name, path in paths.items():
            print(f"{name}: {path.resolve()}")
        return

    cfg = ScannerConfig.from_json(getattr(args, "config", None))
    if args.command == "demo":
        prices, universe = make_demo_data()
        data_as_of = str(prices.date.max().date()) + " (synthetic)"
    else:
        prices, universe = load_prices(args.prices), load_universe(args.universe)
        data_as_of = str(prices.date.max().date())
    ranked, diagnostics = scan_pairs(prices, universe, cfg)
    paths = write_reports(ranked, diagnostics, Path(args.output), cfg, data_as_of)
    tear_sheets = write_tearsheets(ranked, prices, Path(args.output), cfg)
    passed = int(ranked.passes_default_filters.sum()) if not ranked.empty else 0
    print(f"Ranked {len(ranked)} candidate pairs; {passed} pass all default filters.")
    for name, path in paths.items():
        print(f"{name}: {path.resolve()}")
    if tear_sheets:
        print(f"tear_sheets: {(Path(args.output) / 'tear_sheets' / 'index.html').resolve()}")


if __name__ == "__main__":
    main()
