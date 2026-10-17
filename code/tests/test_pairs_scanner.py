from __future__ import annotations

import unittest
import numpy as np
from pathlib import Path
import tempfile

from pairs_scanner.config import ScannerConfig
from pairs_scanner.demo import make_demo_data
from pairs_scanner.scanner import scan_pairs
from pairs_scanner.report import write_reports
from pairs_scanner.statistics import adf_statistic, benjamini_hochberg, cointegration_test, half_life


class StatisticsTests(unittest.TestCase):
    def test_adf_separates_stationary_from_random_walk(self):
        rng = np.random.default_rng(9)
        stationary = np.zeros(1200)
        for i in range(1, len(stationary)):
            stationary[i] = 0.8 * stationary[i - 1] + rng.normal()
        random_walk = np.cumsum(rng.normal(size=1200))
        self.assertLess(adf_statistic(stationary), -3.34)
        self.assertGreater(adf_statistic(random_walk), -3.34)
        self.assertTrue(2 < half_life(stationary) < 10)

    def test_bh_is_monotone_in_pvalue_order(self):
        p = np.array([0.04, 0.001, 0.02, 0.20])
        q = benjamini_hochberg(p)
        ordered = q[np.argsort(p)]
        self.assertTrue(np.all(np.diff(ordered) >= -1e-12))
        self.assertTrue(np.all(q >= p))

    def test_exact_mackinnon_cointegration(self):
        rng = np.random.default_rng(33)
        x = np.cumsum(rng.normal(size=1000))
        y = 1.2 * x + rng.normal(scale=0.5, size=1000)
        stat, pvalue, critical = cointegration_test(y, x, require_exact=True)
        self.assertLess(stat, critical)
        self.assertLess(pvalue, 0.01)


class ScannerTests(unittest.TestCase):
    def test_demo_finds_known_cointegrated_pair(self):
        prices, universe = make_demo_data()
        cfg = ScannerConfig(min_avg_dollar_volume=1_000_000, top_n=20)
        ranked, diagnostics = scan_pairs(prices, universe, cfg)
        pairs = {frozenset((r.first_symbol, r.second_symbol)) for r in ranked.itertuples()}
        self.assertIn(frozenset(("ALFA", "BETA")), pairs)
        self.assertEqual(set(diagnostics.index), set(universe.index))
        target = ranked[
            ranked.apply(lambda r: {r.first_symbol, r.second_symbol} == {"ALFA", "BETA"}, axis=1)
        ].iloc[0]
        self.assertLess(target.adf_stat, -3.34)
        self.assertTrue(np.isfinite(target.score))
        self.assertIn("qualified_setup", ranked.columns)

        with tempfile.TemporaryDirectory() as directory:
            paths = write_reports(ranked, diagnostics, directory, cfg, "synthetic")
            self.assertTrue(all(Path(path).is_file() for path in paths.values()))
            self.assertIn("Daily pairs scanner", Path(paths["html"]).read_text())


if __name__ == "__main__":
    unittest.main()
