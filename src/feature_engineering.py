"""Point-in-time momentum, activity benchmarks, and forward evaluation returns."""

from __future__ import annotations

import pandas as pd

from .config import DEFAULT_CONFIG, ResearchConfig


def add_daily_features(data: pd.DataFrame, config: ResearchConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """Add features; rolling activity averages are shifted to exclude today."""
    frame = data.sort_values(["Symbol", "Date"], kind="stable").copy()
    grouped = frame.groupby("Symbol", sort=False)
    frame["TradedValue"] = frame["Volume"] * frame["Close"]
    for window in config.momentum_windows:
        frame[f"Return_{window}D"] = grouped["Close"].pct_change(window, fill_method=None)
    for source, target in (("Volume", "AvgVolume252"), ("TradedValue", "AvgTradedValue252")):
        frame[target] = frame.groupby("Symbol", sort=False)[source].transform(
            lambda values: values.shift(1).rolling(config.lookback_days, min_periods=config.lookback_days).mean()
        )
    frame["RVOL"] = frame["Volume"].div(frame["AvgVolume252"].where(frame["AvgVolume252"].gt(0)))
    frame["RVAL"] = frame["TradedValue"].div(frame["AvgTradedValue252"].where(frame["AvgTradedValue252"].gt(0)))
    for window in config.forward_windows:
        frame[f"ForwardReturn_{window}D"] = grouped["Close"].shift(-window).div(frame["Close"]).sub(1)
    return frame
