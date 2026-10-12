"""Compact, meeting-friendly daily observation lists."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_observation_lists(panel: pd.DataFrame, output_dir: str | Path,
                            broad_coverage_fraction: float = 0.90) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write the latest available candidates and latest broad-coverage candidate list."""
    if not 0 < broad_coverage_fraction <= 1:
        raise ValueError("broad_coverage_fraction must be in (0, 1]")
    universe_size = int(panel["Symbol"].nunique())
    coverage = panel.groupby("Date")["Symbol"].nunique().rename("SymbolsWithData")
    membership = panel.loc[panel["in_watchlist"].fillna(False)].copy()
    membership["ExpectedSymbols"] = universe_size
    membership = membership.merge(coverage, on="Date", how="left")
    membership["CoveragePct"] = membership["SymbolsWithData"] / universe_size
    membership["CoverageStatus"] = membership["CoveragePct"].ge(broad_coverage_fraction).map(
        {True: "BROAD_COVERAGE", False: "INCOMPLETE_COVERAGE"}
    )
    membership["ActivityQualified"] = membership["signal_or"].fillna(False).astype(bool)
    membership["ResearchStatus"] = membership["ActivityQualified"].map(
        {True: "Momentum + activity expansion", False: "Momentum watchlist only"}
    )
    fields = ["Date", "CoverageStatus", "SymbolsWithData", "ExpectedSymbols", "CoveragePct", "Symbol",
              "Return_3D", "Rank_3D", "Selected_3D", "Return_6D", "Rank_6D", "Selected_6D",
              "Close", "Volume", "TradedValue", "RVOL", "RVAL", "ActivityQualified", "signal_reason", "ResearchStatus"]
    candidates = membership[fields].sort_values(
        ["Date", "ActivityQualified", "Rank_3D", "Rank_6D"],
        ascending=[False, False, True, True], na_position="last"
    ).reset_index(drop=True)
    if candidates.empty:
        raise ValueError("No watchlist candidates are available to report")
    latest_date = candidates["Date"].max()
    latest = candidates.loc[candidates["Date"].eq(latest_date)].copy()
    minimum_coverage = int(universe_size * broad_coverage_fraction + 0.999999)
    broad_dates = coverage.loc[coverage.ge(minimum_coverage)]
    if broad_dates.empty:
        broad = candidates.iloc[0:0].copy()
    else:
        broad_date = broad_dates.index.max()
        broad = candidates.loc[candidates["Date"].eq(broad_date)].copy()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    latest.to_csv(output_path / "latest_observation_candidates.csv", index=False)
    broad.to_csv(output_path / "latest_broad_coverage_observations.csv", index=False)
    return latest, broad
