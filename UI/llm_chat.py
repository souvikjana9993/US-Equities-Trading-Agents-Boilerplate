from __future__ import annotations

import json
from typing import Any

from config import get_llm_config


GROUNDING_RULES = """
Grounding rules:
- Use only the JSON context supplied by the app and the recent conversation.
- Do not invent live prices, financial ratios, company fundamentals, headlines, forecasts, filings, analyst ratings, or portfolio holdings.
- If a value is missing, "N/A", null, simulated, fallback, or demo-only, say that the app does not have enough data for that point.
- Keep numbers exactly as supplied. Do not recalculate unless the prompt gives the formula and all inputs.
- Separate observed data from interpretation. Use words like "the dashboard shows" or "based on the supplied context".
- Treat the selected risk profile as a constraint. A conservative answer should be more cautious than a moderate answer, and a moderate answer should be more cautious than an aggressive answer.
- Do not change supplied scores or recommendations because of risk profile. Explain how the same data should be interpreted for that risk profile.
- Do not present anything as personal financial advice. Frame all buy/sell/hold language as research support or paper-trading simulation.
- If the user asks for data outside the context, explain what additional data source would be needed instead of guessing.

Good example:
"The dashboard shows revenue growth of 12% and positive free cash flow, so the fundamental quality looks strong. I cannot comment on today's news because no fresh headline feed was supplied."

Bad example:
"The stock will beat earnings next quarter" or "analysts upgraded it today" when that information is not in the context.
""".strip()


STOCK_SYSTEM_PROMPT = """
You are the AI chat assistant inside a stock research and paper-trading dashboard.

Your job is to explain the selected ticker using the dashboard data already loaded
by the app. Be concise, practical, and explicit about limitations.

You may explain:
- Recommendation reasoning
- Technical, fundamentals, valuation, news sentiment, portfolio risk, and backtest scores
- Paper-trading implications
- What the user may want to monitor next

{grounding_rules}
""".format(grounding_rules=GROUNDING_RULES).strip()


GENERAL_SYSTEM_PROMPT = """
You are the general AI assistant inside a stock research and paper-trading dashboard.

Help the user understand how to use the app, compare watchlist ideas, interpret
investing concepts, plan paper-trading experiments, and prepare hackathon demos.

You may explain general investing concepts, but when the question is about this
app, the user's portfolio, a ticker, a watchlist item, or a scenario, you must stay
grounded in the supplied app context.

{grounding_rules}
""".format(grounding_rules=GROUNDING_RULES).strip()


def ask_llm(question: str, analysis: dict[str, Any], chat_history: list[tuple[str, str]]) -> str:
    config = get_llm_config()
    prompt = build_prompt(question, analysis, chat_history)

    try:
        return call_openai_responses_api(config, prompt, STOCK_SYSTEM_PROMPT)
    except Exception as error:
        return fallback_error_message(error, config.api_key)


def ask_general_llm(
    question: str,
    app_context: dict[str, Any],
    chat_history: list[tuple[str, str]],
) -> str:
    config = get_llm_config()
    prompt = build_general_prompt(question, app_context, chat_history)

    try:
        return call_openai_responses_api(config, prompt, GENERAL_SYSTEM_PROMPT)
    except Exception as error:
        return fallback_error_message(error, config.api_key)


def call_openai_responses_api(config: Any, prompt: str, system_prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(base_url=config.base_url, api_key=config.api_key)
    response = client.responses.create(
        model=config.model,
        instructions=system_prompt,
        input=[
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
    )
    return extract_response_text(response)


def build_prompt(
    question: str,
    analysis: dict[str, Any],
    chat_history: list[tuple[str, str]],
) -> str:
    context = json.dumps(build_context(analysis), default=str, indent=2)
    return (
        "Grounding contract for this answer:\n"
        "- The JSON below is the only source of stock, portfolio, score, news, and price-history data.\n"
        "- If the answer needs data not present in the JSON, say what is missing.\n"
        "- Do not add outside market knowledge or make unsupported predictions.\n\n"
        "- Use risk_policy as the mandatory style and risk constraint for the answer.\n\n"
        "Current selected-stock dashboard context:\n"
        f"{context}\n\n"
        "Recent conversation:\n"
        f"{format_recent_conversation(chat_history)}\n\n"
        "User question:\n"
        f"{question}"
    )


def build_general_prompt(
    question: str,
    app_context: dict[str, Any],
    chat_history: list[tuple[str, str]],
) -> str:
    context = json.dumps(app_context, default=str, indent=2)
    return (
        "Grounding contract for this answer:\n"
        "- The JSON below is the only source of app, portfolio, watchlist, scenario, and peer-comparison data.\n"
        "- If the answer needs data not present in the JSON, say what is missing.\n"
        "- Do not add outside market knowledge or make unsupported predictions.\n\n"
        "- Use risk_policy as the mandatory style and risk constraint for the answer when it is present.\n\n"
        "Current app context:\n"
        f"{context}\n\n"
        "Recent conversation:\n"
        f"{format_recent_conversation(chat_history)}\n\n"
        "User question:\n"
        f"{question}"
    )


def format_recent_conversation(chat_history: list[tuple[str, str]]) -> str:
    conversation_lines = []
    for role, message in chat_history[-6:]:
        if role in {"user", "assistant"} and message:
            conversation_lines.append(f"{role.title()}: {message}")
    return "\n".join(conversation_lines) or "No previous chat messages."


def build_context(analysis: dict[str, Any]) -> dict[str, Any]:
    final = analysis["final_recommendation"]
    price_history = analysis["price_history"]
    backtest = analysis["backtest"]
    risk_profile = analysis.get("portfolio", {}).get("risk_level", "Moderate")

    return {
        "selected_stock": {
            "ticker": final["ticker"],
            "company": final["company"],
        },
        "risk_policy": risk_policy_for_profile(risk_profile),
        "recommendation": final,
        "price_source": analysis.get("price_source", {}),
        "technical": analysis["technical"],
        "fundamentals": analysis["fundamentals"],
        "news": analysis["news"],
        "valuation": analysis["valuation"],
        "portfolio": analysis["portfolio"],
        "portfolio_risk": analysis["portfolio_risk"],
        "event_risk": analysis["event_risk"],
        "backtest": {
            "total_return": backtest["total_return"],
            "win_rate": backtest["win_rate"],
            "max_drawdown": backtest["max_drawdown"],
            "trades": backtest["trades"],
            "sample_history": table_sample(backtest["history"]),
        },
        "recent_price_history": table_sample(
            price_history[["Date", "Close", "MA50", "MA200", "Volume"]].tail(8)
        ),
    }


def risk_policy_for_profile(risk_profile: str | None) -> dict[str, Any]:
    clean_profile = str(risk_profile or "Moderate").title()
    policies = {
        "Conservative": {
            "risk_profile": "Conservative",
            "llm_behavior": [
                "Prioritize capital preservation, cash discipline, diversification, and downside risk.",
                "Prefer wait, hold, small test-size paper trades, or staged entries unless the dashboard evidence is clearly strong.",
                "Call out concentration, drawdown, valuation, and weak data quality more prominently.",
                "Avoid language that sounds like chasing momentum or accepting large losses.",
            ],
            "paper_trading_guidance": "Use the smallest practical paper size and explain what would invalidate the idea.",
        },
        "Moderate": {
            "risk_profile": "Moderate",
            "llm_behavior": [
                "Balance upside opportunity with drawdown control and portfolio fit.",
                "Support staged paper trades when scores are strong, but keep position caps and cash use visible.",
                "Compare the main positive driver with the main risk before suggesting an action.",
                "Avoid extreme caution or aggressive sizing unless the dashboard context clearly supports it.",
            ],
            "paper_trading_guidance": "Use a balanced paper size, monitor the biggest risk, and keep diversification in view.",
        },
        "Aggressive": {
            "risk_profile": "Aggressive",
            "llm_behavior": [
                "Allow more volatility and growth exposure, but still respect position caps and paper-trading limits.",
                "Explain upside drivers more directly while still naming the downside trigger.",
                "Acknowledge that larger paper trades may be acceptable only when scores, trend, and portfolio fit support it.",
                "Do not ignore concentration, valuation, liquidity, or weak data quality.",
            ],
            "paper_trading_guidance": "A larger paper allocation can be discussed, but only as a simulation with clear risk checks.",
        },
    }
    return policies.get(clean_profile, policies["Moderate"])


def table_sample(table: Any) -> list[dict[str, Any]]:
    if hasattr(table, "to_dict"):
        return table.to_dict("records")
    if isinstance(table, list):
        return table[:8]
    return []


def extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", "")
    if output_text:
        return output_text.strip()

    output = getattr(response, "output", [])
    for item in output:
        for content in getattr(item, "content", []):
            text = getattr(content, "text", "")
            if text:
                return text.strip()

    return "The LLM returned an empty response."


def fallback_error_message(error: Exception, api_key: str) -> str:
    message = str(error)
    if api_key:
        message = message.replace(api_key, "[redacted]")
    return (
        "I could not reach the configured LLM gateway. "
        "Check LITELLM_BASE_URL, LITELLM_API_KEY, and LITELLM_MODEL in .env. "
        f"Error: {message[:300]}"
    )
