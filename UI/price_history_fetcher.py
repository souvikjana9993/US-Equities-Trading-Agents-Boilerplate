from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

import pandas as pd
import yfinance as yf


YAHOO_PERIODS = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y",
}


def fetch_yahoo_price_history(ticker: str, period: str) -> dict[str, Any]:
    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        return empty_price_result("Missing ticker.")

    yahoo_period = YAHOO_PERIODS.get(period, "1y")
    return cached_yahoo_price_history(clean_ticker, yahoo_period)


@lru_cache(maxsize=128)
def cached_yahoo_price_history(ticker: str, yahoo_period: str) -> dict[str, Any]:
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(
            period=yahoo_period,
            interval="1d",
            auto_adjust=True,
        )
    except Exception as error:
        return empty_price_result(str(error))

    frame = clean_price_history(history)
    if frame.empty:
        return empty_price_result("Yahoo Finance did not return price history.")

    return {
        "is_live": True,
        "data_source": "Yahoo Finance",
        "as_of": date.today().isoformat(),
        "history": frame,
        "source_note": "Adjusted daily close and volume pulled from Yahoo Finance through yfinance.",
    }


def clean_price_history(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty or "Close" not in history.columns:
        return pd.DataFrame()

    frame = history.reset_index()
    date_column = "Date" if "Date" in frame.columns else "Datetime"
    if date_column not in frame.columns:
        return pd.DataFrame()

    frame = frame.rename(columns={date_column: "Date"})
    frame = frame[["Date", "Close", "Volume"]].dropna(subset=["Date", "Close"])
    if frame.empty:
        return pd.DataFrame()

    frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame["Volume"] = pd.to_numeric(frame["Volume"], errors="coerce").fillna(0)
    frame = frame.dropna(subset=["Close"]).sort_values("Date")
    if frame.empty:
        return pd.DataFrame()

    frame["Close"] = frame["Close"].round(2)
    frame["Volume"] = frame["Volume"].astype(int)
    frame["MA50"] = frame["Close"].rolling(50, min_periods=1).mean()
    frame["MA200"] = frame["Close"].rolling(200, min_periods=1).mean()
    frame["Daily Return"] = frame["Close"].pct_change().fillna(0)
    return frame.reset_index(drop=True)


def empty_price_result(error_message: str) -> dict[str, Any]:
    return {
        "is_live": False,
        "data_source": "Fallback demo data",
        "as_of": date.today().isoformat(),
        "history": pd.DataFrame(),
        "source_note": f"Using fallback demo price history because Yahoo Finance data was unavailable. {error_message}".strip(),
        "error": error_message,
    }
