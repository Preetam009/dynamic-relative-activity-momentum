import os
import re
import json
import argparse
import pandas as pd
from websocket import create_connection
from session import run as refresh_session
from ingestion_common import append_to_panel, load_ingestion_config, normalize_symbol


SOCKET_URL = "wss://data.tradingview.com/socket.io/websocket"
CSV_COLUMNS = ["TimeStamp", "Open", "High", "Low", "Close", "Volume"]
SERIES_PATTERN = re.compile(r'"s":(\[[\s\S]*?\])(?=,"ns":)')

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(description="Fetch OHLCV data for a TradingView symbol.")
    
    parser.add_argument("symbol", help="Symbol to fetch, for example NSE:NIFTY")
    parser.add_argument("--interval", default="1D", help="TradingView interval")
    parser.add_argument("--bars", type=int, default=100000, help="Number of bars to request",)
    
    return parser.parse_args()

def build_message(function_name: str, arguments: list) -> str:

    payload = json.dumps({"m": function_name, "p": arguments}, separators=(",", ":"))
    
    return f"~m~{len(payload)}~m~{payload}"

def send_message(ws, function_name: str, arguments: list) -> None:

    ws.send(build_message(function_name, arguments))
    
def build_symbol_payload(symbol: str) -> str:

    return "=" + json.dumps(
        {
            "adjustment": "splits",
            "metric": "price",
            "symbol": symbol,
        },
        separators=(",", ":"),
    )
    
def request_series(ws, session_id: str, symbol: str, interval: str, bars: int) -> None:

    send_message(ws, "chart_create_session", [session_id, ""])
    send_message(ws, "resolve_symbol", [session_id, "sds_sym_1", build_symbol_payload(symbol)])
    send_message(ws, "create_series", [session_id, "sds_1", "s1", "sds_sym_1", interval, bars, ""])
    
def receive_series(ws) -> str:

    responses = []

    while True:
        message = ws.recv()
        responses.append(message)
        if "series_completed" in message:
            break

    return "\n".join(responses)

def extract_series_payload(raw_data: str) -> list[dict]:

    match = SERIES_PATTERN.search(raw_data)
    if not match:
        raise ValueError("Unable to find series data in TradingView response")
    
    return json.loads(match.group(1))

def build_dataframe(series_payload: list[dict]) -> pd.DataFrame:

    rows = []

    for item in series_payload:
        values = item.get("v", [])
        if len(values) < 6:
            continue

        rows.append(
            {
                "TimeStamp": pd.to_datetime(values[0], unit="s"),
                "Open": values[1],
                "High": values[2],
                "Low": values[3],
                "Close": values[4],
                "Volume": values[5],
            }
        )

    if not rows:
        raise ValueError("No OHLCV rows were found in TradingView response")

    return pd.DataFrame(rows, columns=CSV_COLUMNS)

def fetch_symbol_dataframe(symbol: str, interval: str, bars: int, session_id: str) -> pd.DataFrame:

    ws = create_connection(SOCKET_URL, timeout=30)
    try:
        request_series(ws, session_id, symbol, interval, bars)
        raw_data = receive_series(ws)
        
    finally:
        ws.close()

    return build_dataframe(extract_series_payload(raw_data))

def fetch_symbol_data(symbol: str, interval: str, bars: int, refresh: bool = True, session_id: str | None = None, output_dir=None,):

    if refresh:
        session_id = refresh_session()

    if session_id is None or output_dir is None:
        session_id, output_dir = load_ingestion_config()

    dataframe = fetch_symbol_dataframe(symbol, interval, bars, session_id)

    normalized_symbol = normalize_symbol(symbol)

    # Save each stock independently.
    output_path = output_dir / f"{normalized_symbol}.csv"

    #dataframe.to_csv(output_path, index=False)
    if os.path.exists(output_path):
        existing_df = pd.read_csv(output_path)
        existing_df["TimeStamp"] = pd.to_datetime(existing_df["TimeStamp"])
        dataframe["TimeStamp"] = pd.to_datetime(dataframe["TimeStamp"])
        combined = pd.concat([existing_df, dataframe], ignore_index=True)
        combined = combined.drop_duplicates(subset=["TimeStamp"], keep="last")
        combined = combined.sort_values(by="TimeStamp").reset_index(drop=True) 
        combined.to_csv(output_path, index=False)
        
    else:
        dataframe = dataframe.sort_values(by="TimeStamp").reset_index(drop=True)
        dataframe.to_csv(output_path, index=False)
    
    return dataframe


def main() -> None:

    args = parse_args()
    dataframe = fetch_symbol_data(args.symbol, args.interval, args.bars)
    print(f"Fetched {len(dataframe)} rows and appended to panel CSV.")


if __name__ == "__main__":
    main()