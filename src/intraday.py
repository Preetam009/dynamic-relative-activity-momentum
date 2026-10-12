"""Future intraday provider contract. Daily CSVs cannot supply live or TOD-normalized data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class MarketDataProvider(ABC):
    """Provider interface for future timestamped intraday bars; no broker client is included."""

    @abstractmethod
    def get_intraday_data(self, symbols: list[str], timestamp: datetime) -> pd.DataFrame:
        """Return observations up to timestamp with Symbol, Timestamp, Close, Volume."""


class IntradayDataUnavailable(RuntimeError):
    """Raised when a caller requests an intraday implementation that is not configured."""
