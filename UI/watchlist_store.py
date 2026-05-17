from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis_engine import WATCHLIST


WATCHLIST_PATH = Path(__file__).resolve().parent / "watchlist.json"


def load_watchlist() -> list[dict[str, str]]:
    if not WATCHLIST_PATH.exists():
        return [dict(item) for item in WATCHLIST]

    try:
        data = json.loads(WATCHLIST_PATH.read_text())
    except json.JSONDecodeError:
        return [dict(item) for item in WATCHLIST]

    if not isinstance(data, list):
        return [dict(item) for item in WATCHLIST]

    cleaned_items = []
    for item in data:
        if isinstance(item, dict) and item.get("ticker"):
            cleaned_items.append(
                {
                    "ticker": str(item["ticker"]).upper(),
                    "signal": str(item.get("signal", "Hold")).title(),
                }
            )
    return cleaned_items or [dict(item) for item in WATCHLIST]


def save_watchlist(items: list[dict[str, Any]]) -> None:
    cleaned_items = []
    seen_tickers = set()
    for item in items:
        ticker = str(item.get("ticker", "")).strip().upper()
        if not ticker or ticker in seen_tickers:
            continue
        seen_tickers.add(ticker)
        cleaned_items.append(
            {
                "ticker": ticker,
                "signal": str(item.get("signal", "Hold")).title(),
            }
        )

    WATCHLIST_PATH.write_text(json.dumps(cleaned_items, indent=2) + "\n")
