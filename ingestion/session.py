import os
import re
import json
from threading import Event
from ingestion_common import ENV_PATH
from dotenv import load_dotenv, set_key
from playwright.sync_api import sync_playwright


CHART_URL = "https://www.tradingview.com/chart/?symbol=NSE:NIFTY"
SESSION_WAIT_ATTEMPTS = 20
SESSION_WAIT_MS = 500
MESSAGE_PATTERN = re.compile(r"~m~(\d+)~m~")

load_dotenv(ENV_PATH)

def parse_tv_messages(data: str) -> list[str]:

    messages = []
    position = 0

    while True:
        match = MESSAGE_PATTERN.search(data, position)
        if not match:
            break

        length = int(match.group(1))
        start = match.end()
        messages.append(data[start : start + length])
        position = start + length

    return messages


def run() -> str:

    session_found = Event()
    captured_session_id: dict[str, str | None] = {"value": None}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        def handle_websocket(websocket) -> None:
            def on_frame_sent(frame: str) -> None:
                for message in parse_tv_messages(frame):
                    if "chart_create_session" not in message:
                        continue

                    session_id = json.loads(message)["p"][0]
                    os.environ["SESSION_ID"] = session_id
                    set_key(str(ENV_PATH), "SESSION_ID", session_id)
                    captured_session_id["value"] = session_id
                    session_found.set()
                    break

            websocket.on("framesent", on_frame_sent)

        page.on("websocket", handle_websocket)
        page.goto(CHART_URL, timeout=60000)

        for _ in range(SESSION_WAIT_ATTEMPTS):
            if session_found.is_set():
                break
            page.wait_for_timeout(SESSION_WAIT_MS)

        browser.close()

    if not captured_session_id["value"]:
        raise RuntimeError("Unable to capture TradingView session ID.")

    return captured_session_id["value"]


if __name__ == "__main__":
    print(run())
