from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

import yfinance as yf


def fetch_company_profile(ticker: str) -> dict[str, Any]:
    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        return empty_profile("Missing ticker.")

    return cached_company_profile(clean_ticker)


@lru_cache(maxsize=256)
def cached_company_profile(ticker: str) -> dict[str, Any]:
    try:
        stock = yf.Ticker(ticker)
        info = load_info(stock)
    except Exception as error:
        return empty_profile(str(error), ticker)

    if not info:
        return empty_profile("Yahoo Finance did not return company profile.", ticker)

    return {
        "is_live": True,
        "data_source": "Yahoo Finance",
        "as_of": date.today().isoformat(),
        "ticker": ticker,
        "company": text_value(info, "shortName", ticker),
        "sector": text_value(info, "sector", "N/A"),
        "industry": text_value(info, "industry", "N/A"),
        "exchange": text_value(info, "exchange", "N/A"),
        "currency": text_value(info, "currency", "N/A"),
        "market_cap": numeric_value(info, "marketCap"),
        "beta": numeric_value(info, "beta"),
        "source_note": "Company profile pulled from Yahoo Finance through yfinance.",
    }


def load_info(stock: yf.Ticker) -> dict[str, Any]:
    try:
        info = stock.get_info()
    except AttributeError:
        info = stock.info
    except Exception:
        info = {}

    return info if isinstance(info, dict) else {}


def text_value(info: dict[str, Any], key: str, fallback: str) -> str:
    value = info.get(key)
    return str(value) if value else fallback


def numeric_value(info: dict[str, Any], key: str) -> float | None:
    value = info.get(key)
    if value in (None, "", "N/A"):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def empty_profile(error_message: str, ticker: str = "N/A") -> dict[str, Any]:
    return {
        "is_live": False,
        "data_source": "Unavailable",
        "as_of": date.today().isoformat(),
        "ticker": ticker,
        "company": ticker,
        "sector": "N/A",
        "industry": "N/A",
        "exchange": "N/A",
        "currency": "N/A",
        "market_cap": None,
        "beta": None,
        "source_note": f"Yahoo Finance company profile unavailable. {error_message}".strip(),
        "error": error_message,
    }
