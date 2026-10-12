"""Command line entry point for the historical daily research pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .analysis import summarize_signals
from .config import DEFAULT_CONFIG
from .data_loader import load_daily_data, load_symbols_file
from .feature_engineering import add_daily_features
from .plots import create_research_plots
from .reporting import write_observation_lists
from .signal_engine import apply_signal_rules
from .universe_selector import build_daily_watchlists

LOGGER = logging.getLogger("dram.research")


def run(data_dir: Path, symbols_file: Path, output_dir: Path, make_plots: bool = True) -> dict[str, object]:
    symbols = load_symbols_file(symbols_file)
    data, issues = load_daily_data(data_dir, symbols)
    features = add_daily_features(data)
    watchlist, _ = build_daily_watchlists(features)
    panel = features.merge(watchlist.drop(columns=["Return_3D", "Rank_3D", "Return_6D", "Rank_6D", "Selected_3D", "Selected_6D", "SelectionType"], errors="ignore"),
                           on=["Date", "Symbol"], how="left")
    panel["in_watchlist"] = panel["in_watchlist"].fillna(False).astype(bool)
    # Restore ranking metadata only for selected observations.
    panel = panel.merge(watchlist.drop(columns="in_watchlist"), on=["Date", "Symbol"], how="left", suffixes=("", "_watch"))
    panel = apply_signal_rules(panel)
    statistics, frequency = summarize_signals(panel, DEFAULT_CONFIG.forward_windows)
    output_dir.mkdir(parents=True, exist_ok=True)
    panel.to_csv(output_dir / "master_daily.csv", index=False)
    panel.to_parquet(output_dir / "master_daily.parquet", index=False)
    watchlist.to_csv(output_dir / "daily_watchlist.csv", index=False)
    panel.loc[panel["signal_or"]].to_csv(output_dir / "signal_events.csv", index=False)
    statistics.to_csv(output_dir / "signal_statistics.csv", index=False)
    frequency.to_csv(output_dir / "signal_frequency.csv", index=False)
    issues_frame = __import__("pandas").DataFrame([{
        **issues, "valid_rows": len(data), "valid_symbols": data.Symbol.nunique(),
        "date_start": data.Date.min(), "date_end": data.Date.max(),
        "watchlist_observations": int(panel.in_watchlist.sum()), "signal_count_or": int(panel.signal_or.sum()),
    }])
    issues_frame.to_csv(output_dir / "validation_report.csv", index=False)
    write_observation_lists(panel, output_dir)
    if make_plots:
        create_research_plots(panel, statistics, output_dir / "plots")
    LOGGER.info("Research complete: %d rows, %d symbols, %d watchlist observations, %d OR signals",
                len(panel), panel.Symbol.nunique(), int(panel.in_watchlist.sum()), int(panel.signal_or.sum()))
    return {"panel": panel, "watchlist": watchlist, "statistics": statistics, "frequency": frequency, "issues": issues}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--symbols", type=Path, default=Path("watchlists/symbols.csv"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run(args.data, args.symbols, args.output, not args.no_plots)


if __name__ == "__main__":
    main()
