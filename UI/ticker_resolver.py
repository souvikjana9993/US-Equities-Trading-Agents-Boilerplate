from __future__ import annotations

import re

import yfinance as yf


LOCAL_COMPANY_TICKERS = {
    "PEPSI": "PEP",
    "PEPSICO": "PEP",
    "PEPSI CO": "PEP",
    "PEPSICO INC": "PEP",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "NVIDIA": "NVDA",
    "TESLA": "TSLA",
    "AMAZON": "AMZN",
    "ALPHABET": "GOOGL",
    "GOOGLE": "GOOGL",
    "WALMART": "WMT",
    "WALMART INC": "WMT",
    "FEDEX": "FDX",
    "FEDEX CORP": "FDX",
    "FEDERAL EXPRESS": "FDX",
}

KNOWN_TICKERS = {
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMZN",
    "GOOGL",
    "PEP",
    "WMT",
    "FDX",
}

US_EXCHANGES = {"NYQ", "NMS", "NAS", "ASE", "PCX", "BTS"}


def resolve_ticker(user_input: str) -> tuple[str, str]:
    search_text = normalize_search_text(user_input)
    if not search_text:
        return "AAPL", "default"

    if search_text in KNOWN_TICKERS or "." in search_text:
        return search_text, "ticker input"

    yahoo_ticker, yahoo_status = search_yahoo_for_ticker(search_text)
    if yahoo_ticker:
        return yahoo_ticker, "Yahoo Finance"

    fallback_ticker = LOCAL_COMPANY_TICKERS.get(search_text)
    if fallback_ticker:
        return fallback_ticker, f"local fallback ({yahoo_status})"

    if looks_like_ticker(search_text):
        return search_text, "ticker input"

    return search_text, f"fallback ({yahoo_status})"


def search_yahoo_for_ticker(search_text: str) -> tuple[str, str]:
    try:
        results = yf.Search(
            search_text,
            max_results=8,
            news_count=0,
            lists_count=0,
            timeout=8,
        )
    except Exception as error:
        return "", f"Yahoo error: {error.__class__.__name__}"

    first_equity_symbol = ""

    for quote in results.quotes:
        if quote.get("quoteType") != "EQUITY":
            continue

        symbol = normalize_symbol(str(quote.get("symbol", "")))
        if not symbol:
            continue

        if not first_equity_symbol:
            first_equity_symbol = symbol

        exchange = quote.get("exchange")
        if "." not in symbol and exchange in US_EXCHANGES:
            return symbol, "request sent"

    if first_equity_symbol:
        return first_equity_symbol, "request sent"

    return "", "Yahoo returned no equity match"


def normalize_search_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().upper())


def normalize_symbol(value: str) -> str:
    return re.sub(r"[^A-Z.]", "", value.upper())[:12]


def looks_like_ticker(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?", value))
