import os
import re
import pandas as pd

from pathlib import Path

from dotenv import dotenv_values

ENV_PATH = ENV_PATH = Path(os.getcwd()) / "ingestion" / "config" / ".env"
DEFAULT_DATA_PATH = "data"
PANEL_CSV_NAME = "daily_panel.csv"

CSV_COLUMNS = ["TimeStamp", "Open", "High", "Low", "Close", "Volume"]

_NORMALIZE_AMBIGUOUS_PAIRS = [
    ("&", "_AMP_"),
    ("-", "_DASH_"),
    (".", "_DOT_"),
    (",", "_COMMA_"),
    ("/", "_SLASH_"),
]

def normalize_symbol(symbol: str) -> str:

    normalized = symbol.upper().strip()
    for char, token in _NORMALIZE_AMBIGUOUS_PAIRS:
        normalized = normalized.replace(char, token)
    normalized = re.sub(r"[^A-Z0-9_]", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized

def resolve_output_dir(data_path: str) -> Path:

    output_dir = Path(data_path)
    if not output_dir.is_absolute():
        output_dir = ENV_PATH.parent / data_path

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def load_ingestion_config() -> tuple[str, Path]:

    config = dotenv_values(ENV_PATH)
    session_id = (config.get("SESSION_ID") or "").strip().strip("'\"")
    data_path = (config.get("DATA_PATH") or DEFAULT_DATA_PATH).strip().strip("'\"")

    if not session_id or session_id.upper() == "NONE":
        raise ValueError("SESSION_ID is missing in ingestion/config/.env")

    return session_id, resolve_output_dir(data_path)

def get_panel_csv_path(output_dir: Path) -> Path:

    return output_dir / PANEL_CSV_NAME


def append_to_panel(dataframe: pd.DataFrame, symbol: str, output_dir: Path) -> None:

    panel_path = get_panel_csv_path(output_dir)

    row = dataframe[CSV_COLUMNS].copy()
    row["Stock"] = normalize_symbol(symbol)
    row["Date"] = pd.to_datetime(row["TimeStamp"], errors="coerce").dt.normalize()
    row["Volume"] = row["Volume"].astype("Int64")
    row = row.dropna(subset=["Date", "Close"])
    row = row.drop(columns=["TimeStamp"])

    if panel_path.exists():
        existing = pd.read_csv(
            panel_path,
            parse_dates=["Date"],
            dtype={"Stock": str, "Open": float, "High": float,
                   "Low": float, "Close": float, "Volume": "Int64"},
        )
        combined = pd.concat([existing, row], ignore_index=True)
        combined = combined.drop_duplicates(subset=["Date", "Stock"], keep="last")
        combined = combined.sort_values(["Date", "Stock"]).reset_index(drop=True)
        try:
            combined.to_csv(panel_path, index=False)
        except OSError as exc:
            raise IOError(f"Failed to write panel CSV: {exc}") from exc
    else:
        try:
            row.to_csv(panel_path, index=False)
        except OSError as exc:
            raise IOError(f"Failed to write panel CSV: {exc}") from exc