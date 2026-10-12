"""Load and validate daily OHLCV CSV files."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from ingestion.ingestion_common import normalize_symbol

LOGGER = logging.getLogger(__name__)
REQUIRED_COLUMNS = ("Date", "Open", "High", "Low", "Close", "Volume")
NUMERIC_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def load_symbols_file(path: str | Path) -> list[str]:
    frame = pd.read_csv(path)
    column = next((c for c in frame.columns if c.strip().lower() in {"symbol", "stock"}), None)
    if column is None:
        raise ValueError(f"No Symbol column in {path}")
    return frame[column].dropna().astype(str).str.strip().loc[lambda s: s.ne("")].drop_duplicates().tolist()


def load_daily_data(data_dir: str | Path, symbols: list[str] | None = None) -> tuple[pd.DataFrame, dict[str, int]]:
    """Load CSVs, normalize dates, remove invalid observations, and report issues."""
    root = Path(data_dir)
    paths = sorted(root.glob("*.csv"))
    if symbols is None:
        files = [(path, path.stem) for path in paths]
        missing_symbols: list[str] = []
    else:
        filename_to_symbol: dict[str, str] = {}
        for symbol in symbols:
            filename = normalize_symbol(symbol)
            previous = filename_to_symbol.get(filename)
            if previous is not None and previous != symbol:
                raise ValueError(f"Symbols {previous!r} and {symbol!r} normalize to the same data filename {filename!r}")
            filename_to_symbol[filename] = symbol
        files = [(path, filename_to_symbol[path.stem]) for path in paths if path.stem in filename_to_symbol]
        found = {path.stem for path, _ in files}
        missing_symbols = sorted(symbol for stem, symbol in filename_to_symbol.items() if stem not in found)
    if not files:
        raise FileNotFoundError(f"No matching OHLCV CSV files found in {root}")
    frames: list[pd.DataFrame] = []
    issues = {"files_discovered": len(paths), "files_requested": len(symbols) if symbols is not None else len(paths),
              "files_loaded": 0, "files_failed": 0, "symbol_files_missing": len(missing_symbols),
              "duplicate_rows": 0, "invalid_rows": 0, "missing_rows": 0}
    if missing_symbols:
        LOGGER.warning("No data CSV found for %d symbols: %s", len(missing_symbols), ", ".join(missing_symbols))
    for path, symbol in files:
        try:
            frame = pd.read_csv(path)
            date_col = "Date" if "Date" in frame.columns else "TimeStamp" if "TimeStamp" in frame.columns else None
            if date_col is None or any(c not in frame.columns for c in NUMERIC_COLUMNS):
                raise ValueError(f"Missing date or OHLCV columns: {path}")
            frame = frame.rename(columns={date_col: "Date"})
            frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.normalize()
            for column in NUMERIC_COLUMNS:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
            frame["Symbol"] = symbol
            issues["missing_rows"] += int(frame[["Date", *NUMERIC_COLUMNS]].isna().any(axis=1).sum())
            frame = frame.dropna(subset=["Date", *NUMERIC_COLUMNS])
            duplicate_mask = frame.duplicated(["Date", "Symbol"], keep="last")
            issues["duplicate_rows"] += int(duplicate_mask.sum())
            frame = frame.loc[~duplicate_mask]
            valid = (frame[["Open", "High", "Low", "Close"]].gt(0).all(axis=1)
                     & frame["Volume"].ge(0)
                     & frame["High"].ge(frame[["Open", "Low", "Close"]].max(axis=1))
                     & frame["Low"].le(frame[["Open", "High", "Close"]].min(axis=1)))
            issues["invalid_rows"] += int((~valid).sum())
            frame = frame.loc[valid, ["Date", "Symbol", *NUMERIC_COLUMNS]]
            if not frame.empty:
                frames.append(frame)
            issues["files_loaded"] += 1
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            issues["files_failed"] += 1
            LOGGER.warning("Failed to load %s: %s", path, exc)
    if not frames:
        raise ValueError(f"No valid rows loaded from {root}")
    data = pd.concat(frames, ignore_index=True).sort_values(["Symbol", "Date"], kind="stable")
    LOGGER.info("Loaded %d rows across %d symbols; %d files failed", len(data), data.Symbol.nunique(), issues["files_failed"])
    return data.reset_index(drop=True), issues
