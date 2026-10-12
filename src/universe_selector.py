"""Daily point-in-time top-gainer watchlist construction."""

from __future__ import annotations

import pandas as pd

from .config import DEFAULT_CONFIG, ResearchConfig


def build_daily_watchlists(features: pd.DataFrame, config: ResearchConfig = DEFAULT_CONFIG) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return one row per date/symbol membership and the de-duplicated watchlist."""
    selections = []
    for window in config.momentum_windows:
        column = f"Return_{window}D"
        eligible = features.dropna(subset=[column]).copy()
        eligible["Rank"] = eligible.groupby("Date")[column].rank(method="first", ascending=False)
        selected = eligible.loc[eligible["Rank"].le(config.top_n), ["Date", "Symbol", column, "Rank"]]
        selected = selected.rename(columns={column: f"Return_{window}D", "Rank": f"Rank_{window}D"})
        selected[f"Selected_{window}D"] = True
        selections.append(selected)
    combined = selections[0].merge(selections[1], on=["Date", "Symbol"], how="outer")
    combined["Selected_3D"] = combined["Selected_3D"].fillna(False).astype(bool)
    combined["Selected_6D"] = combined["Selected_6D"].fillna(False).astype(bool)
    combined["SelectionType"] = combined.apply(
        lambda row: "BOTH" if row.Selected_3D and row.Selected_6D else "3D" if row.Selected_3D else "6D", axis=1
    )
    combined["in_watchlist"] = True
    combined = combined.sort_values(["Date", "Symbol"]).reset_index(drop=True)
    return combined, combined[["Date", "Symbol"]].copy()
