"""Reusable daily research signal rules and structured signal records."""

from __future__ import annotations

import pandas as pd

from .config import DEFAULT_CONFIG, ResearchConfig


def apply_signal_rules(frame: pd.DataFrame, config: ResearchConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    result = frame.copy()
    in_list = result["in_watchlist"].fillna(False).astype(bool)
    rvol = result["RVOL"].ge(config.rvol_threshold).fillna(False)
    rval = result["RVAL"].ge(config.rval_threshold).fillna(False)
    result["signal_momentum"] = in_list
    result["signal_rvol"] = in_list & rvol
    result["signal_rval"] = in_list & rval
    result["signal_or"] = in_list & (rvol | rval)
    result["signal_and"] = in_list & (rvol & rval)
    result["signal"] = result["signal_or"]
    result["signal_reason"] = ""
    result.loc[result["signal_or"] & rvol & ~rval, "signal_reason"] = "RVOL"
    result.loc[result["signal_or"] & rval & ~rvol, "signal_reason"] = "RVAL"
    result.loc[result["signal_and"], "signal_reason"] = "RVOL_AND_RVAL"
    result["timestamp"] = result["Date"]
    return result
