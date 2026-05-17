from __future__ import annotations

import re
from typing import Any

from analysis_engine import get_peer_profiles, get_stock_profile, run_analysis
from llm_chat import risk_policy_for_profile


NEGATIVE_SCENARIO_WORDS = ("drop", "drops", "down", "fall", "falls", "crash", "decline", "loss")
POSITIVE_SCENARIO_WORDS = ("rise", "rises", "up", "gain", "gains", "increase", "rally")
REDUCTION_SCENARIO_WORDS = ("sell", "trim", "reduce", "liquidate", "exit")
ALL_POSITION_WORDS = ("all", "entire", "full", "everything")


def future_watchlist_items(watchlist: list[dict[str, Any]], owned: set[str]) -> list[dict[str, Any]]:
    return [item for item in watchlist if item["ticker"] not in owned]


def compact_analysis_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    final = analysis["final_recommendation"]
    return {
        "ticker": final["ticker"],
        "company": final["company"],
        "recommendation": final["recommendation"],
        "confidence": final["confidence"],
        "final_score": final["final_score"],
        "score_breakdown": final["score_breakdown"],
        "technical_signal": analysis["technical"]["signal"],
        "valuation_signal": analysis["valuation"]["signal"],
        "news_signal": analysis["news"]["signal"],
        "portfolio_fit": analysis["portfolio_risk"]["signal"],
        "portfolio_warning": analysis["portfolio_risk"]["warning"],
        "backtest": {
            "total_return": analysis["backtest"]["total_return"],
            "win_rate": analysis["backtest"]["win_rate"],
            "max_drawdown": analysis["backtest"]["max_drawdown"],
        },
    }


def build_watchlist_rank_context(
    watchlist_items: list[dict[str, Any]],
    period: str,
    risk_profile: str,
    trade_mode: str,
) -> dict[str, Any]:
    candidates = []
    for item in watchlist_items:
        ticker = item["ticker"]
        analysis = run_analysis(ticker, period, risk_profile, trade_mode)
        summary = compact_analysis_summary(analysis)
        summary["watchlist_signal"] = item.get("signal", "Hold")
        candidates.append(summary)

    return {
        "task": "Rank future watchlist tickers by paper-trading research opportunity.",
        "period": period,
        "risk_profile": risk_profile,
        "risk_policy": risk_policy_for_profile(risk_profile),
        "candidates": candidates,
    }


def build_peer_comparison_context(
    analysis: dict[str, Any],
    period: str,
    risk_profile: str,
    trade_mode: str,
) -> dict[str, Any]:
    selected_profile = analysis["profile"]
    selected_ticker = selected_profile.ticker
    selected_sector = selected_profile.sector
    peer_profiles = get_peer_profiles(selected_profile)

    peers = [
        compact_analysis_summary(run_analysis(profile.ticker, period, risk_profile, trade_mode))
        for profile in peer_profiles[:3]
    ]

    return {
        "task": "Compare the selected stock with available peer candidates.",
        "period": period,
        "risk_profile": risk_profile,
        "risk_policy": risk_policy_for_profile(risk_profile),
        "selected": compact_analysis_summary(analysis),
        "peer_selection_basis": f"Prefer same sector peers using Yahoo Finance company profile data. Selected sector: {selected_sector}.",
        "peers": peers,
    }


def build_fallback_plan_context(
    analysis: dict[str, Any],
    scenario_impact: dict[str, Any],
    portfolio_summary: dict[str, Any],
    watchlist_items: list[dict[str, Any]],
    period: str,
    risk_profile: str,
    trade_mode: str,
) -> dict[str, Any]:
    peer_context = build_peer_comparison_context(analysis, period, risk_profile, trade_mode)
    watchlist_context = build_watchlist_rank_context(watchlist_items, period, risk_profile, trade_mode)

    return {
        "task": "Suggest a fallback plan after a what-if portfolio scenario.",
        "rules": [
            "Use only the provided portfolio holdings, future watchlist candidates, and peer candidates.",
            "Do not invent tickers, prices, live market news, or new financial metrics.",
            "Keep the answer practical for paper trading and research support.",
        ],
        "time_period": period,
        "risk_profile": risk_profile,
        "risk_policy": risk_policy_for_profile(risk_profile),
        "trade_mode": trade_mode,
        "scenario_impact": scenario_impact,
        "portfolio_summary": {
            "portfolio_value": portfolio_summary.get("portfolio_value"),
            "unrealized_pnl": portfolio_summary.get("unrealized_pnl"),
            "cash": portfolio_summary.get("cash"),
            "positions": portfolio_summary.get("positions", []),
        },
        "current_stock": compact_analysis_summary(analysis),
        "peer_candidates": peer_context["peers"],
        "future_watchlist_candidates": watchlist_context["candidates"],
    }


def parse_what_if_scenario(
    scenario_text: str,
    selected_ticker: str,
    positions: list[dict[str, Any]],
) -> dict[str, Any]:
    clean_text = scenario_text.strip()
    if not clean_text:
        return {"error": "Enter a scenario such as 'NVDA drops 20%', 'portfolio drops 15%', or 'sell 50% of AAPL'."}

    lower_text = clean_text.lower()
    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", clean_text)
    is_reduction = any(word in lower_text for word in REDUCTION_SCENARIO_WORDS)

    if is_reduction and not percent_match and any(word in lower_text for word in ALL_POSITION_WORDS):
        percent = 100.0
    elif percent_match:
        percent = float(percent_match.group(1))
    else:
        return {"error": "Include a percentage, for example 'AAPL drops 10%' or 'sell 50% of AAPL'."}

    matched_ticker = match_position_ticker(clean_text, selected_ticker, positions)
    is_portfolio_scope = any(word in lower_text for word in ("portfolio", "market", "all holdings", "all stocks"))

    if is_reduction:
        if is_portfolio_scope:
            return {
                "scenario_type": "position_reduction",
                "scope": "portfolio",
                "ticker": None,
                "sell_percent": min(max(percent, 0.0), 100.0),
                "input": clean_text,
            }
        if matched_ticker:
            return {
                "scenario_type": "position_reduction",
                "scope": "ticker",
                "ticker": matched_ticker,
                "sell_percent": min(max(percent, 0.0), 100.0),
                "input": clean_text,
            }
        return {
            "error": "I could not match the sell/reduce scenario to a current holding. Use a ticker from My Portfolio."
        }

    if not percent_match:
        return {"error": "Include a percentage, for example 'AAPL drops 10%'."}

    if any(word in lower_text for word in NEGATIVE_SCENARIO_WORDS):
        percent *= -1
    elif not any(word in lower_text for word in POSITIVE_SCENARIO_WORDS):
        percent *= -1

    if is_portfolio_scope:
        return {
            "scenario_type": "price_move",
            "scope": "portfolio",
            "ticker": None,
            "percent_change": percent,
            "input": clean_text,
        }

    if matched_ticker:
        return {
            "scenario_type": "price_move",
            "scope": "ticker",
            "ticker": matched_ticker,
            "percent_change": percent,
            "input": clean_text,
        }

    return {
        "error": "I could not match the scenario to a current holding. Use a ticker from My Portfolio or say 'portfolio'."
    }


def match_position_ticker(
    scenario_text: str,
    selected_ticker: str,
    positions: list[dict[str, Any]],
) -> str | None:
    lower_text = scenario_text.lower()
    upper_text = scenario_text.upper()
    owned_tickers = [str(position["Ticker"]).upper() for position in positions]

    for ticker in owned_tickers:
        if ticker in upper_text:
            return ticker

    for ticker in owned_tickers:
        profile = get_stock_profile(ticker)
        company_words = profile.company.lower().replace(".", "").split()
        ticker_words = [profile.ticker.lower()]
        candidate_words = ticker_words + [word for word in company_words if len(word) > 3]
        if any(word in lower_text for word in candidate_words):
            return ticker

    selected = selected_ticker.upper()
    if selected in owned_tickers:
        return selected

    return None


def calculate_what_if_impact(
    scenario: dict[str, Any],
    positions: list[dict[str, Any]],
    portfolio_value: float,
) -> dict[str, Any]:
    if "error" in scenario:
        return scenario

    if scenario.get("scenario_type") == "position_reduction":
        return calculate_position_reduction_impact(scenario, positions, portfolio_value)

    percent_change = float(scenario["percent_change"])
    affected_positions = []
    total_change = 0.0

    for position in positions:
        ticker = str(position["Ticker"]).upper()
        if scenario["scope"] == "ticker" and ticker != scenario["ticker"]:
            continue

        market_value = float(position.get("Market Value", 0))
        dollar_change = market_value * percent_change / 100
        total_change += dollar_change
        affected_positions.append(
            {
                "Ticker": ticker,
                "Market Value": round(market_value, 2),
                "Scenario Change": f"{percent_change:.1f}%",
                "Dollar Impact": round(dollar_change, 2),
                "Post Scenario Value": round(market_value + dollar_change, 2),
            }
        )

    if not affected_positions:
        return {"error": "No current holding matched this scenario."}

    new_portfolio_value = portfolio_value + total_change
    portfolio_percent_change = (total_change / portfolio_value * 100) if portfolio_value else 0.0

    return {
        "input": scenario["input"],
        "scenario_type": "price_move",
        "scope": scenario["scope"],
        "ticker": scenario.get("ticker"),
        "percent_change": percent_change,
        "affected_positions": affected_positions,
        "total_dollar_impact": round(total_change, 2),
        "portfolio_value_before": round(portfolio_value, 2),
        "portfolio_value_after": round(new_portfolio_value, 2),
        "portfolio_percent_change": round(portfolio_percent_change, 2),
    }


def calculate_position_reduction_impact(
    scenario: dict[str, Any],
    positions: list[dict[str, Any]],
    portfolio_value: float,
) -> dict[str, Any]:
    sell_percent = float(scenario["sell_percent"])
    affected_positions = []
    cash_generated = 0.0

    for position in positions:
        ticker = str(position["Ticker"]).upper()
        if scenario["scope"] == "ticker" and ticker != scenario["ticker"]:
            continue

        market_value = float(position.get("Market Value", 0))
        quantity = float(position.get("Quantity", 0))
        value_reduced = market_value * sell_percent / 100
        quantity_reduced = quantity * sell_percent / 100
        remaining_value = market_value - value_reduced
        remaining_quantity = quantity - quantity_reduced
        cash_generated += value_reduced

        affected_positions.append(
            {
                "Ticker": ticker,
                "Current Quantity": round(quantity, 4),
                "Quantity Reduced": round(quantity_reduced, 4),
                "Current Market Value": round(market_value, 2),
                "Cash Generated": round(value_reduced, 2),
                "Remaining Quantity": round(remaining_quantity, 4),
                "Remaining Position Value": round(remaining_value, 2),
            }
        )

    if not affected_positions:
        return {"error": "No current holding matched this sell/reduce scenario."}

    return {
        "input": scenario["input"],
        "scenario_type": "position_reduction",
        "scope": scenario["scope"],
        "ticker": scenario.get("ticker"),
        "sell_percent": sell_percent,
        "affected_positions": affected_positions,
        "cash_generated": round(cash_generated, 2),
        "total_dollar_impact": 0.0,
        "portfolio_value_before": round(portfolio_value, 2),
        "portfolio_value_after": round(portfolio_value, 2),
        "portfolio_percent_change": 0.0,
        "note": "This models a paper-trading position reduction. It moves market value into cash and does not assume taxes, fees, slippage, or a price move.",
    }


def sanitize_scenario_for_llm(impact: dict[str, Any]) -> dict[str, Any]:
    clean_impact = dict(impact)
    if clean_impact.get("scenario_type") == "position_reduction":
        clean_impact["input"] = (
            f"Hypothetical paper-trading reduction of {clean_impact.get('sell_percent', 0):.1f}% "
            f"for {clean_impact.get('ticker') or 'current holdings'}."
        )
    return clean_impact


def local_what_if_explanation(impact: dict[str, Any]) -> str:
    if impact.get("scenario_type") == "position_reduction":
        ticker = impact.get("ticker") or "the selected holdings"
        return (
            f"This hypothetical paper-trading reduction converts ${impact['cash_generated']:,.2f} "
            f"of {ticker} exposure into cash. Portfolio value stays about ${impact['portfolio_value_after']:,.2f} "
            "because this scenario does not assume a price move, taxes, fees, or slippage. "
            "The main effect is lower position concentration and higher cash available for future research ideas."
        )

    return (
        f"This scenario changes portfolio value by ${impact['total_dollar_impact']:,.2f}, "
        f"moving it from ${impact['portfolio_value_before']:,.2f} to ${impact['portfolio_value_after']:,.2f}."
    )


def looks_like_llm_refusal(answer: str) -> bool:
    lower_answer = answer.lower()
    refusal_markers = (
        "i'm sorry",
        "i am sorry",
        "i cannot assist",
        "can't assist",
        "cannot provide",
    )
    return any(marker in lower_answer for marker in refusal_markers)


def trade_note_fallback(trade: dict[str, Any], analysis: dict[str, Any]) -> str:
    final = analysis["final_recommendation"]
    return (
        f"{trade['action']} simulation for {trade['quantity']:,.4f} shares of {trade['ticker']} "
        f"at ${trade['price']:,.2f}. The dashboard recommendation was {final['recommendation']} "
        f"with {final['confidence']}% confidence at the time of the paper trade."
    )
