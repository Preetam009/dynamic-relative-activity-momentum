"""Unit checks for point-in-time calculations and signal conditions."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.config import ResearchConfig
from src.feature_engineering import add_daily_features
from src.data_loader import load_daily_data
from src.signal_engine import apply_signal_rules
from src.universe_selector import build_daily_watchlists


class ResearchTests(unittest.TestCase):
    def test_loader_resolves_normalized_symbol_filenames(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "NAM_DASH_INDIA.csv"
            path.write_text("TimeStamp,Open,High,Low,Close,Volume\n2024-01-02,10,11,9,10,100\n")
            loaded, issues = load_daily_data(temp_dir, ["NAM-INDIA"])
        self.assertEqual(loaded.Symbol.tolist(), ["NAM-INDIA"])
        self.assertEqual(issues["files_loaded"], 1)
        self.assertEqual(issues["symbol_files_missing"], 0)

    def test_returns_traded_value_and_prior_only_rolling_average(self):
        data = pd.DataFrame({"Date": pd.date_range("2020-01-01", periods=260), "Symbol": "AAA",
                             "Open": 1.0, "High": 1.0, "Low": 1.0,
                             "Close": range(1, 261), "Volume": [100.0] * 259 + [10000.0]})
        features = add_daily_features(data, ResearchConfig(lookback_days=3))
        row = features.iloc[259]
        self.assertAlmostEqual(row.Return_3D, 3 / 257)
        self.assertAlmostEqual(row.Return_6D, 6 / 254)
        self.assertEqual(row.TradedValue, 260 * 10000)
        self.assertEqual(row.AvgVolume252, 100)
        self.assertEqual(row.AvgTradedValue252, sum((i * 100 for i in range(257, 260)))/3)

    def test_top_n_and_deduplication(self):
        rows = []
        for symbol, value in zip("ABCDEFGHIJK", range(11)):
            rows.append({"Date": pd.Timestamp("2024-01-01"), "Symbol": symbol,
                         "Return_3D": value, "Return_6D": value})
        watchlist, _ = build_daily_watchlists(pd.DataFrame(rows), ResearchConfig(top_n=2))
        self.assertEqual(len(watchlist), 2)
        self.assertEqual(set(watchlist.Symbol), {"J", "K"})
        self.assertTrue(watchlist.Selected_3D.all() and watchlist.Selected_6D.all())

    def test_signal_variants_require_watchlist_and_threshold(self):
        rows = pd.DataFrame({"Date": pd.date_range("2024-01-01", periods=5), "Symbol": list("ABCDE"),
                             "in_watchlist": [True, True, False, True, True],
                             "RVOL": [2.1, 1.5, 10.0, 0.9, 2.3], "RVAL": [0.8, 1.9, 10.0, 2.1, 2.2]})
        result = apply_signal_rules(rows)
        self.assertTrue(result.loc[0, "signal_or"])
        self.assertEqual(result.loc[0, "signal_reason"], "RVOL")
        self.assertFalse(result.loc[1, "signal_or"])
        self.assertFalse(result.loc[2, "signal_or"])
        self.assertTrue(result.loc[3, "signal_rval"])
        self.assertEqual(result.loc[3, "signal_reason"], "RVAL")
        self.assertTrue(result.loc[4, "signal_and"])
        self.assertEqual(result.loc[4, "signal_reason"], "RVOL_AND_RVAL")


if __name__ == "__main__":
    unittest.main()
