"""Central research parameters for the daily breakout study."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchConfig:
    top_n: int = 10
    momentum_windows: tuple[int, ...] = (3, 6)
    lookback_days: int = 252
    rvol_threshold: float = 2.0
    rval_threshold: float = 2.0
    forward_windows: tuple[int, ...] = (1, 3, 5, 10)


DEFAULT_CONFIG = ResearchConfig()
