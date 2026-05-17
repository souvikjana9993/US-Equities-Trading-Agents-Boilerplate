from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

import pandas as pd
import yfinance as yf


def fetch_yfinance_fundamentals(ticker: str) -> dict[str, Any]:
    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        return empty_result("Missing ticker.")

    return cached_yfinance_fundamentals(clean_ticker)


@lru_cache(maxsize=128)
def cached_yfinance_fundamentals(ticker: str) -> dict[str, Any]:
    try:
        stock = yf.Ticker(ticker)
        info = load_info(stock)
        financials = load_table(stock, "financials")
        balance_sheet = load_table(stock, "balance_sheet")
        cashflow = load_table(stock, "cashflow")
    except Exception as error:
        return empty_result(str(error))

    if not info and tables_are_empty(financials, balance_sheet, cashflow):
        return empty_result("Yahoo Finance did not return fundamentals.")

    raw_values = build_raw_values(info, financials, balance_sheet, cashflow)
    score = score_fundamentals(raw_values)

    return {
        "is_live": True,
        "data_source": "Yahoo Finance",
        "as_of": date.today().isoformat(),
        "score": score,
        "signal": signal_from_score(score),
        "company": text_value(info, "shortName", ticker),
        "sector": text_value(info, "sector", "N/A"),
        "industry": text_value(info, "industry", "N/A"),
        "website": text_value(info, "website", "N/A"),
        "market_cap": format_money(raw_values["market_cap"]),
        "enterprise_value": format_money(raw_values["enterprise_value"]),
        "total_revenue": format_money(raw_values["total_revenue"]),
        "gross_profit": format_money(raw_values["gross_profit"]),
        "net_income": format_money(raw_values["net_income"]),
        "ebitda": format_money(raw_values["ebitda"]),
        "operating_cash_flow": format_money(raw_values["operating_cash_flow"]),
        "free_cash_flow": format_money(raw_values["free_cash_flow"]),
        "total_cash": format_money(raw_values["total_cash"]),
        "total_debt": format_money(raw_values["total_debt"]),
        "revenue_growth": format_percent(raw_values["revenue_growth"]),
        "eps_growth": format_percent(raw_values["eps_growth"]),
        "earnings_growth": format_percent(raw_values["earnings_growth"]),
        "profit_margin": format_percent(raw_values["profit_margin"]),
        "operating_margin": format_percent(raw_values["operating_margin"]),
        "gross_margin": format_percent(raw_values["gross_margin"]),
        "ebitda_margin": format_percent(raw_values["ebitda_margin"]),
        "return_on_equity": format_percent(raw_values["return_on_equity"]),
        "dividend_yield": format_percent(raw_values["dividend_yield"]),
        "payout_ratio": format_percent(raw_values["payout_ratio"]),
        "pe_ratio": format_number(raw_values["pe_ratio"]),
        "forward_pe": format_number(raw_values["forward_pe"]),
        "peg_ratio": format_number(raw_values["peg_ratio"]),
        "price_to_sales": format_number(raw_values["price_to_sales"]),
        "price_to_book": format_number(raw_values["price_to_book"]),
        "enterprise_to_revenue": format_number(raw_values["enterprise_to_revenue"]),
        "enterprise_to_ebitda": format_number(raw_values["enterprise_to_ebitda"]),
        "debt_to_equity": format_number(raw_values["debt_to_equity"]),
        "current_ratio": format_number(raw_values["current_ratio"]),
        "quick_ratio": format_number(raw_values["quick_ratio"]),
        "beta": format_number(raw_values["beta"]),
        "trailing_eps": format_number(raw_values["trailing_eps"]),
        "forward_eps": format_number(raw_values["forward_eps"]),
        "book_value": format_number(raw_values["book_value"]),
        "revenue_per_share": format_number(raw_values["revenue_per_share"]),
        "total_cash_per_share": format_number(raw_values["total_cash_per_share"]),
        "shares_outstanding": format_number(raw_values["shares_outstanding"], decimals=0),
        "strengths": build_strengths(raw_values),
        "weaknesses": build_weaknesses(raw_values),
        "source_note": "Live fundamentals pulled from Yahoo Finance through yfinance.",
        "_raw": raw_values,
    }


def load_info(stock: yf.Ticker) -> dict[str, Any]:
    try:
        info = stock.get_info()
    except AttributeError:
        info = stock.info
    except Exception:
        info = {}

    return info if isinstance(info, dict) else {}


def load_table(stock: yf.Ticker, attribute_name: str) -> pd.DataFrame:
    try:
        table = getattr(stock, attribute_name)
    except Exception:
        return pd.DataFrame()

    return table if isinstance(table, pd.DataFrame) else pd.DataFrame()


def tables_are_empty(*tables: pd.DataFrame) -> bool:
    return all(table.empty for table in tables)


def build_raw_values(
    info: dict[str, Any],
    financials: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> dict[str, float | None]:
    total_revenue = numeric_value(info, "totalRevenue") or statement_value(
        financials,
        ["Total Revenue", "TotalRevenue"],
    )
    gross_profit = numeric_value(info, "grossProfits") or statement_value(
        financials,
        ["Gross Profit", "GrossProfit"],
    )
    total_debt = numeric_value(info, "totalDebt") or statement_value(
        balance_sheet,
        ["Total Debt", "TotalDebt", "Long Term Debt"],
    )
    total_cash = numeric_value(info, "totalCash") or statement_value(
        balance_sheet,
        ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
    )

    free_cash_flow = numeric_value(info, "freeCashflow") or statement_value(
        cashflow,
        ["Free Cash Flow", "FreeCashFlow"],
    )
    operating_cash_flow = numeric_value(info, "operatingCashflow") or statement_value(
        cashflow,
        ["Operating Cash Flow", "OperatingCashFlow"],
    )
    if free_cash_flow is None:
        capital_expenditure = statement_value(cashflow, ["Capital Expenditure", "CapitalExpenditure"])
        if operating_cash_flow is not None and capital_expenditure is not None:
            free_cash_flow = operating_cash_flow + capital_expenditure

    revenue_growth = numeric_value(info, "revenueGrowth") or growth_from_statement(
        financials,
        ["Total Revenue", "TotalRevenue"],
    )
    debt_to_equity = normalize_debt_to_equity(numeric_value(info, "debtToEquity"))

    return {
        "market_cap": numeric_value(info, "marketCap"),
        "enterprise_value": numeric_value(info, "enterpriseValue"),
        "total_revenue": total_revenue,
        "gross_profit": gross_profit,
        "net_income": numeric_value(info, "netIncomeToCommon") or statement_value(
            financials,
            ["Net Income", "NetIncome", "Net Income Common Stockholders"],
        ),
        "ebitda": numeric_value(info, "ebitda"),
        "operating_cash_flow": operating_cash_flow,
        "free_cash_flow": free_cash_flow,
        "total_cash": total_cash,
        "total_debt": total_debt,
        "revenue_growth": revenue_growth,
        "eps_growth": numeric_value(info, "earningsGrowth") or numeric_value(info, "earningsQuarterlyGrowth"),
        "earnings_growth": numeric_value(info, "earningsQuarterlyGrowth"),
        "profit_margin": numeric_value(info, "profitMargins"),
        "operating_margin": numeric_value(info, "operatingMargins"),
        "gross_margin": numeric_value(info, "grossMargins"),
        "ebitda_margin": numeric_value(info, "ebitdaMargins"),
        "return_on_equity": numeric_value(info, "returnOnEquity"),
        "dividend_yield": numeric_value(info, "dividendYield"),
        "payout_ratio": numeric_value(info, "payoutRatio"),
        "pe_ratio": numeric_value(info, "trailingPE"),
        "forward_pe": numeric_value(info, "forwardPE"),
        "peg_ratio": numeric_value(info, "pegRatio"),
        "price_to_sales": numeric_value(info, "priceToSalesTrailing12Months"),
        "price_to_book": numeric_value(info, "priceToBook"),
        "enterprise_to_revenue": numeric_value(info, "enterpriseToRevenue"),
        "enterprise_to_ebitda": numeric_value(info, "enterpriseToEbitda"),
        "debt_to_equity": debt_to_equity,
        "current_ratio": numeric_value(info, "currentRatio"),
        "quick_ratio": numeric_value(info, "quickRatio"),
        "beta": numeric_value(info, "beta"),
        "trailing_eps": numeric_value(info, "trailingEps"),
        "forward_eps": numeric_value(info, "forwardEps"),
        "book_value": numeric_value(info, "bookValue"),
        "revenue_per_share": numeric_value(info, "revenuePerShare"),
        "total_cash_per_share": numeric_value(info, "totalCashPerShare"),
        "shares_outstanding": numeric_value(info, "sharesOutstanding"),
    }


def statement_value(table: pd.DataFrame, labels: list[str]) -> float | None:
    if table.empty:
        return None

    normalized_index = {str(index).lower().replace(" ", ""): index for index in table.index}
    for label in labels:
        key = label.lower().replace(" ", "")
        if key not in normalized_index:
            continue

        row = table.loc[normalized_index[key]].dropna()
        if row.empty:
            continue
        return safe_float(row.iloc[0])

    return None


def growth_from_statement(table: pd.DataFrame, labels: list[str]) -> float | None:
    if table.empty:
        return None

    normalized_index = {str(index).lower().replace(" ", ""): index for index in table.index}
    for label in labels:
        key = label.lower().replace(" ", "")
        if key not in normalized_index:
            continue

        row = table.loc[normalized_index[key]].dropna()
        if len(row) < 2:
            continue

        latest = safe_float(row.iloc[0])
        previous = safe_float(row.iloc[1])
        if latest is None or previous in (None, 0):
            continue
        return (latest - previous) / abs(previous)

    return None


def numeric_value(info: dict[str, Any], key: str) -> float | None:
    return safe_float(info.get(key))


def text_value(info: dict[str, Any], key: str, fallback: str) -> str:
    value = info.get(key)
    return str(value) if value else fallback


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    return number


def normalize_debt_to_equity(value: float | None) -> float | None:
    if value is None:
        return None
    if value > 10:
        return value / 100
    return value


def score_fundamentals(values: dict[str, float | None]) -> int:
    score = 50

    revenue_growth = values["revenue_growth"]
    if revenue_growth is not None:
        if revenue_growth >= 0.10:
            score += 12
        elif revenue_growth > 0:
            score += 6
        else:
            score -= 10

    eps_growth = values["eps_growth"]
    if eps_growth is not None:
        if eps_growth >= 0.10:
            score += 10
        elif eps_growth > 0:
            score += 5
        else:
            score -= 8

    profit_margin = values["profit_margin"]
    if profit_margin is not None:
        if profit_margin >= 0.20:
            score += 10
        elif profit_margin >= 0.10:
            score += 6
        elif profit_margin < 0:
            score -= 12

    operating_margin = values["operating_margin"]
    if operating_margin is not None and operating_margin >= 0.15:
        score += 6

    free_cash_flow = values["free_cash_flow"]
    if free_cash_flow is not None:
        score += 8 if free_cash_flow > 0 else -8

    debt_to_equity = values["debt_to_equity"]
    if debt_to_equity is not None:
        if debt_to_equity <= 1:
            score += 8
        elif debt_to_equity >= 2:
            score -= 8

    return max(1, min(99, score))


def signal_from_score(score: int) -> str:
    if score >= 75:
        return "Strong"
    if score >= 58:
        return "Stable"
    return "Weak"


def build_strengths(values: dict[str, float | None]) -> str:
    strengths = []
    if is_positive(values["revenue_growth"]):
        strengths.append("revenue growth")
    if is_positive(values["free_cash_flow"]):
        strengths.append("free cash flow")
    if values["profit_margin"] is not None and values["profit_margin"] >= 0.10:
        strengths.append("profitability")
    if values["debt_to_equity"] is not None and values["debt_to_equity"] <= 1:
        strengths.append("manageable leverage")
    return ", ".join(strengths) if strengths else "No clear fundamental strength found in available Yahoo Finance fields."


def build_weaknesses(values: dict[str, float | None]) -> str:
    weaknesses = []
    if values["revenue_growth"] is not None and values["revenue_growth"] < 0:
        weaknesses.append("negative revenue growth")
    if values["eps_growth"] is not None and values["eps_growth"] < 0:
        weaknesses.append("negative EPS growth")
    if values["debt_to_equity"] is not None and values["debt_to_equity"] >= 2:
        weaknesses.append("higher leverage")
    if values["pe_ratio"] is not None and values["pe_ratio"] >= 35:
        weaknesses.append("elevated PE ratio")
    return ", ".join(weaknesses) if weaknesses else "No major weakness found in available Yahoo Finance fields."


def is_positive(value: float | None) -> bool:
    return value is not None and value > 0


def format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def format_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def format_money(value: float | None) -> str:
    if value is None:
        return "N/A"

    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.0f}"


def empty_result(error_message: str) -> dict[str, Any]:
    return {
        "is_live": False,
        "data_source": "Fallback",
        "as_of": date.today().isoformat(),
        "error": error_message,
    }
