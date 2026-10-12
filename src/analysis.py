"""Forward-return summaries and frequency metrics for strategy variants."""

from __future__ import annotations

import pandas as pd

STRATEGIES = {"Momentum": "signal_momentum", "RVOL": "signal_rvol", "RVAL": "signal_rval",
              "OR": "signal_or", "AND": "signal_and"}


def summarize_signals(frame: pd.DataFrame, forward_windows: tuple[int, ...] = (1, 3, 5, 10)) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries = []
    frequency = []
    watchlist_count = int(frame["in_watchlist"].fillna(False).sum())
    days = max(frame["Date"].nunique(), 1)
    symbols = max(frame["Symbol"].nunique(), 1)
    for strategy, signal_col in STRATEGIES.items():
        selected = frame.loc[frame[signal_col].fillna(False)]
        for window in forward_windows:
            col = f"ForwardReturn_{window}D"
            returns = selected[col].dropna()
            summaries.append({"Strategy": strategy, "HorizonDays": window, "SignalCount": len(selected),
                "EvaluatedCount": len(returns), "MeanReturn": returns.mean(), "MedianReturn": returns.median(),
                "WinRate": returns.gt(0).mean(), "StdReturn": returns.std(), "MinReturn": returns.min(),
                "MaxReturn": returns.max(), **{f"Q{q:02d}": returns.quantile(q / 100) for q in (5, 25, 50, 75, 95)}})
        frequency.append({"Strategy": strategy, "SignalCount": len(selected),
            "SignalsPerTradingDay": len(selected) / days, "SignalsPerStock": len(selected) / symbols,
            "WatchlistObservationRate": len(selected) / watchlist_count if watchlist_count else float("nan")})
    return pd.DataFrame(summaries), pd.DataFrame(frequency)
