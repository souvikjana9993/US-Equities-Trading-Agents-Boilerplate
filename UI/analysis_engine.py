from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from math import sin
from pathlib import Path
from typing import Any

import pandas as pd

from company_profile_fetcher import fetch_company_profile
from fundamentals_fetcher import fetch_yfinance_fundamentals
from price_history_fetcher import fetch_yahoo_price_history


PORTFOLIO_PATH = Path(__file__).resolve().parent / "paper_portfolio.json"


@dataclass(frozen=True)
class StockProfile:
    ticker: str
    company: str
    sector: str
    start_price: float
    trend: float
    volatility: float
    base_score: int
    industry: str = "N/A"
    profile_source: str = "Fallback"
    profile_note: str = ""


STOCK_PROFILES: dict[str, StockProfile] = {
    "AAPL": StockProfile("AAPL", "Apple Inc.", "Technology", 183.0, 0.18, 0.020, 76),
    "MSFT": StockProfile("MSFT", "Microsoft Corp.", "Technology", 414.0, 0.22, 0.018, 80),
    "NVDA": StockProfile("NVDA", "NVIDIA Corp.", "Semiconductors", 940.0, 0.33, 0.032, 84),
    "TSLA": StockProfile("TSLA", "Tesla Inc.", "Consumer Cyclical", 178.0, -0.06, 0.041, 59),
    "AMZN": StockProfile("AMZN", "Amazon.com Inc.", "Consumer Cyclical", 182.0, 0.15, 0.025, 72),
    "GOOGL": StockProfile("GOOGL", "Alphabet Inc.", "Communication Services", 171.0, 0.13, 0.022, 74),
    "PEP": StockProfile("PEP", "PepsiCo Inc.", "Consumer Staples", 172.0, 0.07, 0.014, 69),
    "WMT": StockProfile("WMT", "Walmart Inc.", "Consumer Staples", 67.0, 0.11, 0.013, 71),
    "FDX": StockProfile("FDX", "FedEx Corp.", "Industrials", 312.0, 0.05, 0.026, 63),
    "PUM.DE": StockProfile("PUM.DE", "PUMA SE", "Consumer Cyclical", 45.0, 0.03, 0.024, 61),
}

WATCHLIST = [
    {"ticker": "AAPL", "signal": "Buy"},
    {"ticker": "MSFT", "signal": "Buy"},
    {"ticker": "TSLA", "signal": "Hold"},
    {"ticker": "NVDA", "signal": "Buy"},
    {"ticker": "WMT", "signal": "Hold"},
]

PEER_UNIVERSE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMZN",
    "GOOGL",
    "PEP",
    "WMT",
    "FDX",
    "JPM",
    "PBYI",
]

PERIOD_DAYS = {
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 252,
    "5Y": 1260,
}


def get_stock_profile(ticker: str) -> StockProfile:
    clean_ticker = ticker.strip().upper() or "AAPL"
    profile_data = fetch_company_profile(clean_ticker)
    hint = STOCK_PROFILES.get(clean_ticker)

    if profile_data.get("is_live"):
        return StockProfile(
            ticker=clean_ticker,
            company=profile_data["company"],
            sector=profile_data["sector"],
            start_price=hint.start_price if hint else fallback_start_price(clean_ticker),
            trend=hint.trend if hint else 0.0,
            volatility=hint.volatility if hint else 0.024,
            base_score=profile_base_score(profile_data),
            industry=profile_data["industry"],
            profile_source=profile_data["data_source"],
            profile_note=profile_data["source_note"],
        )

    if hint:
        return StockProfile(
            ticker=hint.ticker,
            company=hint.company,
            sector=hint.sector,
            start_price=hint.start_price,
            trend=hint.trend,
            volatility=hint.volatility,
            base_score=hint.base_score,
            industry=hint.industry,
            profile_source="Fallback profile hint",
            profile_note=profile_data.get("source_note", ""),
        )

    return StockProfile(
        ticker=clean_ticker,
        company=clean_ticker,
        sector="N/A",
        start_price=fallback_start_price(clean_ticker),
        trend=0.0,
        volatility=0.024,
        base_score=55,
        profile_source="Unavailable",
        profile_note=profile_data.get("source_note", ""),
    )


def fallback_start_price(ticker: str) -> float:
    seed = sum(ord(char) for char in ticker)
    return float(75 + seed % 250)


def profile_base_score(profile_data: dict[str, Any]) -> int:
    score = 58
    if profile_data.get("sector") not in {"", "N/A", None}:
        score += 4
    if profile_data.get("market_cap"):
        score += 6
    beta = profile_data.get("beta")
    if isinstance(beta, (int, float)):
        if beta <= 1.2:
            score += 3
        elif beta >= 1.8:
            score -= 5
    return clamp(score)


def get_peer_profiles(selected_profile: StockProfile, max_peers: int = 3) -> list[StockProfile]:
    selected_sector = selected_profile.sector
    peer_profiles = [
        get_stock_profile(ticker)
        for ticker in PEER_UNIVERSE
        if ticker != selected_profile.ticker
    ]

    same_sector = [
        profile
        for profile in peer_profiles
        if profile.sector == selected_sector and selected_sector not in {"", "N/A", None}
    ]
    if len(same_sector) >= max_peers:
        return same_sector[:max_peers]

    remaining = [
        profile
        for profile in peer_profiles
        if profile not in same_sector
    ]
    return (same_sector + remaining)[:max_peers]


def build_price_history(profile: StockProfile, period: str) -> pd.DataFrame:
    yahoo_result = fetch_yahoo_price_history(profile.ticker, period)
    if yahoo_result.get("is_live"):
        frame = yahoo_result["history"]
        frame.attrs["is_live"] = True
        frame.attrs["data_source"] = yahoo_result["data_source"]
        frame.attrs["source_note"] = yahoo_result["source_note"]
        frame.attrs["as_of"] = yahoo_result["as_of"]
        return frame

    frame = build_demo_price_history(profile, period)
    frame.attrs["is_live"] = False
    frame.attrs["data_source"] = "Fallback demo data"
    frame.attrs["source_note"] = yahoo_result.get("source_note", "Using fallback demo price history.")
    frame.attrs["as_of"] = date.today().isoformat()
    return frame


def build_demo_price_history(profile: StockProfile, period: str) -> pd.DataFrame:
    days = PERIOD_DAYS.get(period, 252)
    end_date = date.today()
    dates = [end_date - timedelta(days=days - index - 1) for index in range(days)]

    seed = sum(ord(char) for char in profile.ticker)
    prices: list[float] = []
    volumes: list[int] = []

    for index in range(days):
        progress = index / max(days - 1, 1)
        cycle = sin(index / 7 + seed) * profile.volatility
        slow_cycle = sin(index / 31 + seed / 3) * profile.volatility * 1.4
        price = profile.start_price * (1 + profile.trend * progress + cycle + slow_cycle)
        prices.append(round(max(price, 5), 2))
        volumes.append(int(2_000_000 + (seed % 60) * 75_000 + abs(sin(index / 5)) * 1_500_000))

    frame = pd.DataFrame({"Date": pd.to_datetime(dates), "Close": prices, "Volume": volumes})
    frame["MA50"] = frame["Close"].rolling(50, min_periods=1).mean()
    frame["MA200"] = frame["Close"].rolling(200, min_periods=1).mean()
    frame["Daily Return"] = frame["Close"].pct_change().fillna(0)
    return frame


def calculate_rsi(prices: pd.Series, window: int = 14) -> float:
    delta = prices.diff().fillna(0)
    gains = delta.clip(lower=0).rolling(window, min_periods=1).mean()
    losses = delta.clip(upper=0).abs().rolling(window, min_periods=1).mean()
    relative_strength = gains.iloc[-1] / max(losses.iloc[-1], 0.01)
    return round(100 - (100 / (1 + relative_strength)), 1)


def technical_score_from_price(
    period_return: float,
    latest_price: float,
    ma50: float,
    ma200: float,
    rsi: float,
) -> int:
    score = 50
    score += int(max(min(period_return, 35), -35) * 0.7)

    if latest_price > ma50:
        score += 8
    else:
        score -= 8

    if latest_price > ma200:
        score += 8
    else:
        score -= 8

    if 45 <= rsi <= 65:
        score += 7
    elif 35 <= rsi < 45 or 65 < rsi <= 75:
        score += 2
    else:
        score -= 6

    return clamp(score)


def estimated_selected_position_daily_pnl(price_history: pd.DataFrame, quantity: float) -> float:
    if quantity <= 0 or len(price_history) < 2:
        return 0.0
    latest_price = float(price_history["Close"].iloc[-1])
    previous_price = float(price_history["Close"].iloc[-2])
    return round((latest_price - previous_price) * quantity, 2)


def run_analysis(
    ticker: str,
    period: str,
    risk_profile: str,
    trade_mode: str,
) -> dict[str, Any]:
    profile = get_stock_profile(ticker)
    price_history = build_price_history(profile, period)
    price_source = build_price_source(price_history)
    latest_price = float(price_history["Close"].iloc[-1])
    first_price = float(price_history["Close"].iloc[0])
    period_return = (latest_price / first_price - 1) * 100
    rsi = calculate_rsi(price_history["Close"])

    technical_score = technical_score_from_price(
        period_return,
        latest_price,
        float(price_history["MA50"].iloc[-1]),
        float(price_history["MA200"].iloc[-1]),
        rsi,
    )
    news_score = clamp(profile.base_score - 3 + len(profile.ticker))
    fundamentals = fetch_yfinance_fundamentals(profile.ticker)
    if fundamentals.get("is_live"):
        fundamentals_score = int(fundamentals["score"])
    else:
        fundamentals_score = 55
        fundamentals = fallback_fundamentals(profile, fundamentals_score, 55, fundamentals.get("error"))
    valuation = build_valuation(fundamentals, latest_price)
    valuation_score = int(valuation["score"])
    portfolio_risk = build_portfolio_risk(profile, risk_profile, 0)
    portfolio_score = int(portfolio_risk["score"])
    event_score = clamp(66 - (8 if profile.ticker in {"TSLA", "NVDA"} else 0))

    final_score = round(
        technical_score * 0.24
        + fundamentals_score * 0.20
        + news_score * 0.16
        + valuation_score * 0.16
        + portfolio_score * 0.16
        + event_score * 0.08,
        1,
    )
    recommendation = recommendation_from_score(final_score, risk_profile)
    confidence = clamp(int(final_score + 7 if recommendation == "Buy" else final_score))
    max_allocation = allocation_for_risk(risk_profile, recommendation)
    suggested_buy_amount = int(float(portfolio_risk.get("portfolio_value", 0)) * max_allocation)
    portfolio_risk = build_portfolio_risk(profile, risk_profile, suggested_buy_amount)

    return {
        "profile": profile,
        "price_history": price_history,
        "price_source": price_source,
        "portfolio": {
            "value": portfolio_risk.get("portfolio_value", 0),
            "today_pnl": estimated_selected_position_daily_pnl(
                price_history,
                float(portfolio_risk.get("selected_quantity", 0)),
            ),
            "cash": portfolio_risk.get("cash", 0),
            "risk_level": risk_profile,
            "trade_mode": trade_mode,
            "current_holding": portfolio_risk.get("selected_quantity", 0),
        },
        "technical": {
            "score": technical_score,
            "signal": signal_from_score(technical_score),
            "rsi": rsi,
            "macd": "Positive" if period_return > 2 else "Negative",
            "volume_trend": "Rising" if price_history["Volume"].iloc[-1] > price_history["Volume"].tail(20).mean() else "Stable",
            "summary": technical_summary(latest_price, price_history["MA50"].iloc[-1], price_history["MA200"].iloc[-1], rsi),
        },
        "fundamentals": fundamentals,
        "news": {
            "score": news_score,
            "signal": sentiment_from_score(news_score),
            "themes": ["earnings outlook", "analyst coverage", "demand trends"],
            "positive_headlines": [
                f"{profile.company} sees constructive analyst commentary",
                f"{profile.sector} demand remains a support for revenue growth",
            ],
            "negative_headlines": [
                "Higher rates continue to pressure market multiples",
                "Investors remain selective ahead of the next earnings cycle",
            ],
            "summary": f"Recent simulated news flow is {sentiment_from_score(news_score).lower()}, with demand and analyst commentary offset by macro caution.",
        },
        "valuation": valuation,
        "portfolio_risk": portfolio_risk,
        "event_risk": {
            "score": event_score,
            "signal": "Normal" if event_score >= 60 else "Elevated",
            "notes": ["Monitor earnings date", "Watch guidance changes", "Track analyst revisions"],
        },
        "backtest": build_backtest(profile, period_return),
        "final_recommendation": {
            "ticker": profile.ticker,
            "company": profile.company,
            "recommendation": recommendation,
            "confidence": confidence,
            "final_score": final_score,
            "suggested_action": suggested_action(recommendation, risk_profile, suggested_buy_amount, trade_mode),
            "reasoning": final_reasoning(recommendation, technical_score, fundamentals_score, valuation_score, portfolio_score),
            "risk_warnings": [portfolio_risk["warning"], "This is a simulation for research and paper trading only."],
            "score_breakdown": {
                "Technical": technical_score,
                "Fundamentals": fundamentals_score,
                "News Sentiment": news_score,
                "Valuation": valuation_score,
                "Portfolio Fit": portfolio_score,
                "Event Risk": event_score,
            },
        },
    }


def clamp(value: int, lower: int = 1, upper: int = 99) -> int:
    return max(lower, min(upper, value))


def build_price_source(price_history: pd.DataFrame) -> dict[str, Any]:
    return {
        "is_live": bool(price_history.attrs.get("is_live", False)),
        "data_source": price_history.attrs.get("data_source", "Fallback demo data"),
        "source_note": price_history.attrs.get("source_note", "Price history source unavailable."),
        "as_of": price_history.attrs.get("as_of", date.today().isoformat()),
    }


def build_valuation(fundamentals: dict[str, Any], latest_price: float) -> dict[str, Any]:
    raw_values = fundamentals.get("_raw", {})
    market_cap = raw_values.get("market_cap")
    free_cash_flow = raw_values.get("free_cash_flow")
    fcf_yield = None
    if market_cap and free_cash_flow:
        fcf_yield = free_cash_flow / market_cap

    score = valuation_score_from_raw(raw_values, fcf_yield)
    return {
        "score": score,
        "signal": valuation_signal(score),
        "current_price": latest_price,
        "data_source": fundamentals.get("data_source", "N/A"),
        "source_note": valuation_source_note(fundamentals),
        "pe_ratio": fundamentals.get("pe_ratio", "N/A"),
        "forward_pe": fundamentals.get("forward_pe", "N/A"),
        "peg_ratio": fundamentals.get("peg_ratio", "N/A"),
        "price_to_sales": fundamentals.get("price_to_sales", "N/A"),
        "price_to_book": fundamentals.get("price_to_book", "N/A"),
        "enterprise_to_revenue": fundamentals.get("enterprise_to_revenue", "N/A"),
        "enterprise_to_ebitda": fundamentals.get("enterprise_to_ebitda", "N/A"),
        "fcf_yield": format_percent_value(fcf_yield),
        "valuation_notes": valuation_notes(raw_values, fcf_yield),
    }


def valuation_source_note(fundamentals: dict[str, Any]) -> str:
    if fundamentals.get("is_live"):
        return "Valuation uses Yahoo Finance ratios already loaded in the Fundamentals tab."
    return "Valuation is limited because Yahoo Finance fundamentals were unavailable."


def valuation_score_from_raw(raw_values: dict[str, float | None], fcf_yield: float | None) -> int:
    subscores = []
    add_subscore(subscores, raw_values.get("pe_ratio"), [(18, 82), (28, 68), (40, 52)], 38)
    add_subscore(subscores, raw_values.get("forward_pe"), [(18, 82), (28, 68), (40, 52)], 38)
    add_subscore(subscores, raw_values.get("peg_ratio"), [(1.2, 82), (2.0, 66), (3.0, 50)], 35)
    add_subscore(subscores, raw_values.get("price_to_sales"), [(3.0, 78), (7.0, 62), (12.0, 48)], 35)
    add_subscore(subscores, raw_values.get("price_to_book"), [(4.0, 76), (10.0, 60), (20.0, 45)], 35)
    add_subscore(subscores, raw_values.get("enterprise_to_ebitda"), [(14.0, 78), (24.0, 62), (35.0, 48)], 35)
    if fcf_yield is not None:
        if fcf_yield >= 0.06:
            subscores.append(82)
        elif fcf_yield >= 0.035:
            subscores.append(68)
        elif fcf_yield > 0:
            subscores.append(54)
        else:
            subscores.append(35)

    if not subscores:
        return 55
    return clamp(round(sum(subscores) / len(subscores)))


def add_subscore(
    subscores: list[int],
    value: float | None,
    thresholds: list[tuple[float, int]],
    high_value_score: int,
) -> None:
    if value is None or value <= 0:
        return

    for threshold, score in thresholds:
        if value <= threshold:
            subscores.append(score)
            return
    subscores.append(high_value_score)


def valuation_notes(raw_values: dict[str, float | None], fcf_yield: float | None) -> list[str]:
    notes = []
    pe_ratio = raw_values.get("pe_ratio")
    peg_ratio = raw_values.get("peg_ratio")
    ev_ebitda = raw_values.get("enterprise_to_ebitda")

    if pe_ratio:
        notes.append(f"Trailing PE is {pe_ratio:.2f}.")
    if peg_ratio:
        notes.append(f"PEG ratio is {peg_ratio:.2f}.")
    if ev_ebitda:
        notes.append(f"EV/EBITDA is {ev_ebitda:.2f}.")
    if fcf_yield is not None:
        notes.append(f"Free-cash-flow yield is {fcf_yield * 100:.1f}%.")

    return notes or ["Yahoo Finance did not provide enough valuation ratios for a strong valuation read."]


def format_percent_value(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def build_portfolio_risk(
    profile: StockProfile,
    risk_profile: str,
    suggested_buy_amount: int,
) -> dict[str, Any]:
    portfolio = load_portfolio_snapshot()
    positions = portfolio["positions"]
    cash = portfolio["cash"]
    market_value = sum(position["market_value"] for position in positions)
    portfolio_value = cash + market_value

    selected_sector = profile.sector or "N/A"
    sector_value = sum(
        position["market_value"]
        for position in positions
        if position["sector"] == selected_sector
    )
    selected_value = sum(
        position["market_value"]
        for position in positions
        if position["ticker"] == profile.ticker
    )
    selected_quantity = sum(
        position["quantity"]
        for position in positions
        if position["ticker"] == profile.ticker
    )

    current_sector_exposure = percent_of(sector_value, portfolio_value)
    selected_position_exposure = percent_of(selected_value, portfolio_value)

    post_portfolio_value = portfolio_value + max(suggested_buy_amount, 0)
    post_sector_value = sector_value + max(suggested_buy_amount, 0)
    post_trade_exposure = percent_of(post_sector_value, post_portfolio_value)

    score = portfolio_score_from_exposure(
        current_sector_exposure,
        selected_position_exposure,
        risk_profile,
        selected_sector,
    )

    return {
        "score": score,
        "signal": "Fits profile" if score >= 65 else "Position cap needed",
        "sector": selected_sector,
        "current_sector_exposure": round(current_sector_exposure, 1),
        "selected_position_exposure": round(selected_position_exposure, 1),
        "post_trade_exposure": round(post_trade_exposure, 1),
        "suggested_position_size": suggested_buy_amount,
        "portfolio_value": round(portfolio_value, 2),
        "cash": round(cash, 2),
        "selected_quantity": round(selected_quantity, 4),
        "data_source": "Current paper portfolio holdings with Yahoo Finance prices and sectors when available.",
        "warning": portfolio_risk_warning(
            profile.ticker,
            selected_sector,
            risk_profile,
            suggested_buy_amount,
            current_sector_exposure,
            post_trade_exposure,
            score,
        ),
    }


def load_portfolio_snapshot() -> dict[str, Any]:
    try:
        portfolio = json.loads(PORTFOLIO_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"cash": 0.0, "positions": []}

    trades = portfolio.get("trades", [])
    positions: dict[str, dict[str, float]] = {}
    last_trade_price: dict[str, float] = {}

    for trade in sorted(trades, key=lambda item: item.get("trade_date", "")):
        ticker = str(trade.get("ticker", "")).upper()
        if not ticker:
            continue

        positions.setdefault(ticker, {"quantity": 0.0, "cost_basis": 0.0})
        quantity = float(trade.get("quantity", 0))
        trade_value = float(trade.get("trade_value", 0))
        price = float(trade.get("price", 0))
        if price > 0:
            last_trade_price[ticker] = price

        if str(trade.get("action", "")).title() == "Buy":
            positions[ticker]["quantity"] += quantity
            positions[ticker]["cost_basis"] += trade_value
        else:
            current_quantity = positions[ticker]["quantity"]
            if current_quantity <= 0:
                continue
            sell_quantity = min(quantity, current_quantity)
            average_cost = positions[ticker]["cost_basis"] / current_quantity
            positions[ticker]["quantity"] -= sell_quantity
            positions[ticker]["cost_basis"] -= average_cost * sell_quantity

    rows = []
    for ticker, position in positions.items():
        quantity = position["quantity"]
        if quantity <= 0:
            continue
        current_price = latest_price_for_ticker(ticker, last_trade_price.get(ticker, 0))
        current_profile = get_stock_profile(ticker)
        rows.append(
            {
                "ticker": ticker,
                "sector": current_profile.sector,
                "quantity": quantity,
                "market_value": quantity * current_price,
            }
        )

    return {
        "cash": float(portfolio.get("cash", 0)),
        "positions": rows,
    }


def latest_price_for_ticker(ticker: str, fallback_price: float) -> float:
    price_result = fetch_yahoo_price_history(ticker, "1M")
    if price_result.get("is_live"):
        history = price_result["history"]
        if not history.empty:
            return float(history["Close"].iloc[-1])
    return fallback_price if fallback_price > 0 else 0.0


def percent_of(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return part / total * 100


def portfolio_score_from_exposure(
    sector_exposure: float,
    selected_position_exposure: float,
    risk_profile: str,
    sector: str,
) -> int:
    sector_limit = {"Conservative": 25, "Moderate": 35, "Aggressive": 45}[risk_profile]
    position_limit = {"Conservative": 10, "Moderate": 15, "Aggressive": 22}[risk_profile]

    score = 88
    if sector in {"", "N/A", None}:
        score -= 8
    if sector_exposure > sector_limit:
        score -= int((sector_exposure - sector_limit) * 1.2)
    if selected_position_exposure > position_limit:
        score -= int((selected_position_exposure - position_limit) * 1.8)
    return clamp(score)


def portfolio_risk_warning(
    ticker: str,
    sector: str,
    risk_profile: str,
    suggested_buy_amount: int,
    current_exposure: float,
    post_exposure: float,
    score: int,
) -> str:
    if score < 65:
        return (
            f"{ticker} needs position discipline for a {risk_profile.lower()} profile. "
            f"{sector} exposure is {current_exposure:.1f}% now and would be {post_exposure:.1f}% after the paper trade."
        )
    if suggested_buy_amount > 0:
        return (
            f"{ticker} fits the current paper portfolio profile. "
            f"Suggested cap is ${suggested_buy_amount:,.0f}; {sector} exposure would move to {post_exposure:.1f}%."
        )
    return (
        f"{ticker} does not require a new paper trade from the current signal. "
        f"{sector} exposure is {current_exposure:.1f}%."
    )


def sector_quality_adjustment(sector: str) -> int:
    if sector in {"Technology", "Semiconductors"}:
        return 4
    if sector == "Consumer Cyclical":
        return -2
    return 1


def portfolio_fit_score(profile: StockProfile, risk_profile: str) -> int:
    score = profile.base_score - (10 if profile.sector in {"Technology", "Semiconductors"} else 0)
    if risk_profile == "Conservative":
        score -= 8
    elif risk_profile == "Aggressive":
        score += 7
    return clamp(score)


def allocation_for_risk(risk_profile: str, recommendation: str) -> float:
    if recommendation != "Buy":
        return 0.0
    return {"Conservative": 0.02, "Moderate": 0.04, "Aggressive": 0.06}[risk_profile]


def recommendation_from_score(score: float, risk_profile: str) -> str:
    buy_threshold = 73 if risk_profile == "Conservative" else 68
    sell_threshold = 46 if risk_profile == "Aggressive" else 50
    if score >= buy_threshold:
        return "Buy"
    if score <= sell_threshold:
        return "Sell"
    return "Hold"


def signal_from_score(score: int) -> str:
    if score >= 70:
        return "Bullish"
    if score <= 50:
        return "Bearish"
    return "Neutral"


def business_signal(score: int) -> str:
    if score >= 75:
        return "Strong"
    if score >= 58:
        return "Stable"
    return "Weak"


def fallback_fundamentals(
    profile: StockProfile,
    fundamentals_score: int,
    valuation_score: int,
    error_message: str | None,
) -> dict[str, Any]:
    return {
        "is_live": False,
        "data_source": "Unavailable",
        "as_of": date.today().isoformat(),
        "score": fundamentals_score,
        "signal": "Unavailable",
        "company": profile.company,
        "sector": profile.sector,
        "industry": "N/A",
        "website": "N/A",
        "market_cap": "N/A",
        "enterprise_value": "N/A",
        "total_revenue": "N/A",
        "gross_profit": "N/A",
        "net_income": "N/A",
        "ebitda": "N/A",
        "operating_cash_flow": "N/A",
        "revenue_growth": "N/A",
        "eps_growth": "N/A",
        "earnings_growth": "N/A",
        "pe_ratio": "N/A",
        "forward_pe": "N/A",
        "peg_ratio": "N/A",
        "price_to_sales": "N/A",
        "price_to_book": "N/A",
        "enterprise_to_revenue": "N/A",
        "enterprise_to_ebitda": "N/A",
        "debt_to_equity": "N/A",
        "current_ratio": "N/A",
        "quick_ratio": "N/A",
        "profit_margin": "N/A",
        "operating_margin": "N/A",
        "gross_margin": "N/A",
        "ebitda_margin": "N/A",
        "return_on_equity": "N/A",
        "free_cash_flow": "N/A",
        "total_cash": "N/A",
        "total_debt": "N/A",
        "beta": "N/A",
        "dividend_yield": "N/A",
        "payout_ratio": "N/A",
        "trailing_eps": "N/A",
        "forward_eps": "N/A",
        "book_value": "N/A",
        "revenue_per_share": "N/A",
        "total_cash_per_share": "N/A",
        "shares_outstanding": "N/A",
        "strengths": "N/A - Yahoo Finance fundamentals were unavailable.",
        "weaknesses": "N/A - Yahoo Finance fundamentals were unavailable.",
        "source_note": f"Fundamentals unavailable from Yahoo Finance. {error_message or ''}".strip(),
        "_raw": {},
    }


def sentiment_from_score(score: int) -> str:
    if score >= 68:
        return "Positive"
    if score >= 52:
        return "Mixed"
    return "Negative"


def valuation_signal(score: int) -> str:
    if score >= 72:
        return "Attractive"
    if score >= 55:
        return "Fair"
    return "Expensive"


def technical_summary(latest_price: float, ma50: float, ma200: float, rsi: float) -> str:
    trend_text = "above" if latest_price > ma50 and latest_price > ma200 else "near or below"
    return f"Price is {trend_text} the key moving averages. RSI is {rsi}, which suggests momentum without relying on a single indicator."


def portfolio_warning(profile: StockProfile, risk_profile: str, suggested_buy_amount: int) -> str:
    if suggested_buy_amount <= 0:
        return f"{profile.ticker} should stay on watch until the signal improves for a {risk_profile.lower()} profile."
    if profile.sector in {"Technology", "Semiconductors"}:
        return f"Buying {profile.ticker} increases {profile.sector} exposure; cap the paper trade near ${suggested_buy_amount:,.0f}."
    return f"Position size is acceptable for the selected profile; suggested cap is ${suggested_buy_amount:,.0f}."


def suggested_action(recommendation: str, risk_profile: str, amount: int, trade_mode: str) -> str:
    if recommendation == "Buy":
        return f"{trade_mode}: buy up to ${amount:,.0f} for a {risk_profile.lower()} risk profile."
    if recommendation == "Sell":
        return f"{trade_mode}: reduce exposure or avoid a new position until conditions improve."
    return f"{trade_mode}: hold or watch; wait for a clearer technical or valuation setup."


def final_reasoning(recommendation: str, technical: int, fundamentals: int, valuation: int, portfolio: int) -> str:
    return (
        f"The {recommendation.lower()} call combines technical score {technical}, fundamentals score {fundamentals}, "
        f"valuation score {valuation}, and portfolio fit score {portfolio}. The app favors balanced evidence over one signal."
    )


def build_backtest(profile: StockProfile, period_return: float) -> dict[str, Any]:
    total_return = round(period_return * 0.68 + (profile.base_score - 60) * 0.12, 1)
    win_rate = clamp(52 + int(total_return / 2), 35, 78)
    max_drawdown = round(-1 * (6 + profile.volatility * 150), 1)
    trades = 10 + profile.base_score % 13
    history = pd.DataFrame(
        {
            "Trade": [1, 2, 3, 4, 5],
            "Signal": ["Buy", "Hold", "Buy", "Sell", "Buy"],
            "Return": [2.4, 0.8, -1.6, 3.1, round(total_return / 5, 1)],
        }
    )
    return {
        "total_return": total_return,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "trades": trades,
        "history": history,
    }


def answer_question(question: str, analysis: dict[str, Any]) -> str:
    final = analysis["final_recommendation"]
    portfolio = analysis["portfolio_risk"]
    technical = analysis["technical"]
    valuation = analysis["valuation"]
    lower_question = question.lower()

    if "risk" in lower_question:
        return f"The biggest risk is portfolio fit: {portfolio['warning']} Valuation is {valuation['signal'].lower()}, so position size matters."
    if "why" in lower_question or "buy" in lower_question or "sell" in lower_question:
        return f"{final['ticker']} is rated {final['recommendation']} because {final['reasoning']} Suggested action: {final['suggested_action']}"
    if "$" in question or "invest" in lower_question:
        return f"Use the suggested paper-trade cap before sizing an order. Current cap: ${portfolio['suggested_position_size']:,.0f}. Larger trades may increase concentration risk."
    if "wait" in lower_question or "earnings" in lower_question:
        return "Waiting can be reasonable when event risk is near earnings. The current simulated event notes are: monitor earnings date, guidance changes, and analyst revisions."
    return f"Current view: {final['recommendation']} with {final['confidence']}% confidence. Technical signal is {technical['signal']} and valuation is {valuation['signal']}."
