import csv
import sys
import time
import argparse
import subprocess
from pathlib import Path
from session import run as refresh_session
from tv_socket_fetch import fetch_symbol_data
from ingestion_common import load_ingestion_config


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CSV_FILE = BASE_DIR.parent / "watchlists" / "symbols.csv"
DEFAULT_SCRIPT = BASE_DIR / "tv_socket_fetch.py"

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(description="Read symbols from a CSV file and fetch TradingView data for each one.")
    
    parser.add_argument("--csv-file", default=str(DEFAULT_CSV_FILE), help="Path to the CSV file containing symbols",)
    parser.add_argument("--column", default="symbol", help="Name of the column containing symbols",)
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between requests",)
    parser.add_argument("--interval", default="1D", help="TradingView interval",)
    parser.add_argument("--bars", type=int, default=100000, help="Number of bars to request",)
    parser.add_argument("--mode", choices=["direct", "subprocess"], default="direct", help="Use direct in-process fetching or the legacy subprocess mode",)
    
    return parser.parse_args()

def resolve_column(fieldnames: list[str] | None, column_name: str) -> str:

    if not fieldnames:
        raise ValueError("The CSV file is empty or missing a header row.")

    lookup = {name.strip().lower(): name for name in fieldnames}
    match = lookup.get(column_name.strip().lower())
    
    if match is None:
        raise ValueError(f"Column '{column_name}' not found. Available columns: {', '.join(fieldnames)}")
    
    return match

def load_symbols(csv_file: str, column_name: str) -> list[str]:

    csv_path = Path(csv_file)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        resolved_column = resolve_column(reader.fieldnames, column_name)

        symbols = []
        
        for row_number, row in enumerate(reader, start=2):
            symbol = (row.get(resolved_column) or "").strip()
            
            if not symbol:
                print(f"Skipping empty symbol at row {row_number}")
                continue
            
            symbols.append(symbol)

    if not symbols:
        raise ValueError(f"No symbols found in column '{column_name}' of {csv_path}")

    return symbols

def run_fetch_direct(symbol: str, interval: str, bars: int, session_id: str, output_dir, refresh_session_fn=None,) -> None:

    try:
        fetch_symbol_data(symbol, interval, bars, refresh=False, session_id=session_id, output_dir=output_dir,)
        
    except Exception as exc:

        if refresh_session_fn is not None:
            session_id = refresh_session_fn()
            fetch_symbol_data(symbol, interval, bars, refresh=False, session_id=session_id, output_dir=output_dir,)
            
        else:
            raise exc
        
def run_fetch_subprocess(script_path: Path, symbol: str, interval: str, bars: int) -> None:

    command = [sys.executable, str(script_path), symbol, "--interval", interval, "--bars", str(bars),]
    subprocess.run(command, check=True)
    
def process_symbols(symbols: list[str], args: argparse.Namespace) -> list[str]:

    total = len(symbols)
    failures = []
    delay_seconds = args.delay
    session_id = None
    output_dir = None

    if args.mode == "direct":
        session_id = refresh_session()
        _, output_dir = load_ingestion_config()

    refresh_fn = refresh_session if args.mode == "direct" else None

    for index, symbol in enumerate(symbols, start=1):
        print(f"[{index}/{total}] Processing {symbol}...")

        try:
            if args.mode == "direct":
                run_fetch_direct(symbol, args.interval, args.bars, session_id, output_dir, refresh_fn)
                
            else:
                run_fetch_subprocess(DEFAULT_SCRIPT, symbol, args.interval, args.bars)
                
        except Exception as exc:
            print(f"Failed to process {symbol}: {exc}")
            failures.append(symbol)
            continue

        if index < total and delay_seconds > 0:
            time.sleep(delay_seconds)

    return failures


def main() -> None:

    args = parse_args()
    symbols = load_symbols(args.csv_file, args.column)
    failures = process_symbols(symbols, args)

    if failures:
        print(f"Finished with {len(failures)} failures: {', '.join(failures)}")
    else:
        print("Finished processing all symbols.")


if __name__ == "__main__":
    
    try:
        main()
        
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)