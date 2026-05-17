from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yfinance as yf


PORTFOLIO_PATH = Path(__file__).resolve().parent / "paper_portfolio.json"
STARTING_CASH = 100_000.0

SEED_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "PUM.DE"]

FALLBACK_PRICES = {
    "AAPL": 185.0,
    "MSFT": 420.0,
    "TSLA": 190.0,
    "NVDA": 900.0,
    "PUM.DE": 45.0,
}


def load_paper_portfolio() -> dict[str, Any]:
    if not PORTFOLIO_PATH.exists():
        portfolio = seed_paper_portfolio()
        save_paper_portfolio(portfolio)
        return portfolio

    try:
        portfolio = json.loads(PORTFOLIO_PATH.read_text())
    except json.JSONDecodeError:
        portfolio = seed_paper_portfolio()
        save_paper_portfolio(portfolio)
        return portfolio

    if not isinstance(portfolio, dict) or "trades" not in portfolio:
        portfolio = seed_paper_portfolio()
        save_paper_portfolio(portfolio)

    return portfolio


def save_paper_portfolio(portfolio: dict[str, Any]) -> None:
    PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2) + "\n")


def seed_paper_portfolio() -> dict[str, Any]:
    rng = random.Random(42)
    today = date.today()
    start_date = today - timedelta(days=365)
    trades = []
    cash = STARTING_CASH

    for ticker in SEED_TICKERS:
        price_history = get_price_history(ticker)
        trade_dates = sorted(
            start_date + timedelta(days=rng.randint(15, 350))
            for _ in range(rng.randint(2, 4))
        )

        for trade_date in trade_dates:
            price = price_for_date(ticker, price_history, trade_date)
            trade_value = float(rng.randrange(1_000, 5_000, 250))
            quantity = round(trade_value / price, 4)

            cash -= trade_value
            trades.append(
                {
                    "trade_date": trade_date.isoformat(),
                    "ticker": ticker,
                    "action": "Buy",
                    "input_mode": "Seeded historical buy",
                    "quantity": quantity,
                    "price": round(price, 2),
                    "trade_value": round(trade_value, 2),
                }
            )

    return {
        "starting_cash": STARTING_CASH,
        "cash": round(cash, 2),
        "trades": trades,
    }


def get_price_history(ticker: str) -> list[dict[str, Any]]:
    try:
        frame = yf.Ticker(ticker).history(period="1y", interval="1d")
    except Exception:
        return []

    if frame.empty:
        return []

    frame = frame.reset_index()
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "date": row["Date"].date(),
                "close": float(row["Close"]),
            }
        )
    return rows


def price_for_date(ticker: str, price_history: list[dict[str, Any]], trade_date: date) -> float:
    if not price_history:
        return FALLBACK_PRICES.get(ticker, 100.0)

    available_rows = [row for row in price_history if row["date"] <= trade_date]
    if available_rows:
        return available_rows[-1]["close"]

    return price_history[0]["close"]


def current_price_for_ticker(ticker: str, trades: list[dict[str, Any]]) -> float:
    try:
        frame = yf.Ticker(ticker).history(period="5d", interval="1d")
        if not frame.empty:
            return float(frame["Close"].iloc[-1])
    except Exception:
        pass

    ticker_trades = [trade for trade in trades if trade["ticker"] == ticker]
    if ticker_trades:
        return float(ticker_trades[-1]["price"])

    return FALLBACK_PRICES.get(ticker, 100.0)


def add_trade(portfolio: dict[str, Any], trade: dict[str, Any]) -> dict[str, Any]:
    clean_trade = {
        "trade_date": trade.get("trade_date", datetime.now().date().isoformat()),
        "ticker": str(trade["ticker"]).upper(),
        "action": str(trade["action"]).title(),
        "input_mode": str(trade.get("input_mode", "")),
        "quantity": round(float(trade["quantity"]), 4),
        "price": round(float(trade["price"]), 2),
        "trade_value": round(float(trade["trade_value"]), 2),
    }
    if trade.get("trade_note"):
        clean_trade["trade_note"] = str(trade["trade_note"])

    portfolio.setdefault("trades", []).append(clean_trade)
    portfolio.setdefault("cash", STARTING_CASH)

    if clean_trade["action"] == "Buy":
        portfolio["cash"] = round(float(portfolio["cash"]) - clean_trade["trade_value"], 2)
    else:
        portfolio["cash"] = round(float(portfolio["cash"]) + clean_trade["trade_value"], 2)

    save_paper_portfolio(portfolio)
    return portfolio


def update_cash_balance(portfolio: dict[str, Any], cash_balance: float) -> dict[str, Any]:
    portfolio.setdefault("starting_cash", STARTING_CASH)
    portfolio.setdefault("trades", [])
    portfolio["cash"] = round(float(cash_balance), 2)
    save_paper_portfolio(portfolio)
    return portfolio


def summarize_portfolio(portfolio: dict[str, Any]) -> dict[str, Any]:
    trades = portfolio.get("trades", [])
    positions: dict[str, dict[str, float]] = {}

    for trade in sorted(trades, key=lambda item: item["trade_date"]):
        ticker = trade["ticker"]
        positions.setdefault(ticker, {"quantity": 0.0, "cost_basis": 0.0})

        quantity = float(trade["quantity"])
        trade_value = float(trade["trade_value"])

        if trade["action"] == "Buy":
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
    total_market_value = 0.0
    total_cost_basis = 0.0

    for ticker, position in positions.items():
        quantity = round(position["quantity"], 4)
        if quantity <= 0:
            continue

        current_price = current_price_for_ticker(ticker, trades)
        market_value = quantity * current_price
        cost_basis = position["cost_basis"]
        unrealized_pnl = market_value - cost_basis
        average_cost = cost_basis / quantity if quantity else 0.0

        total_market_value += market_value
        total_cost_basis += cost_basis
        rows.append(
            {
                "Ticker": ticker,
                "Quantity": quantity,
                "Avg Cost": round(average_cost, 2),
                "Current Price": round(current_price, 2),
                "Market Value": round(market_value, 2),
                "Unrealized P&L": round(unrealized_pnl, 2),
            }
        )

    cash = float(portfolio.get("cash", STARTING_CASH))
    return {
        "cash": round(cash, 2),
        "positions": rows,
        "market_value": round(total_market_value, 2),
        "portfolio_value": round(cash + total_market_value, 2),
        "cost_basis": round(total_cost_basis, 2),
        "unrealized_pnl": round(total_market_value - total_cost_basis, 2),
        "trade_count": len(trades),
    }
