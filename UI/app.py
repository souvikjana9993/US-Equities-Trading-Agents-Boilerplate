from __future__ import annotations

from html import escape
import sys
from pathlib import Path

import streamlit as st

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from ai_feature_helpers import (
    build_fallback_plan_context,
    build_peer_comparison_context,
    calculate_what_if_impact,
    future_watchlist_items,
    local_what_if_explanation,
    looks_like_llm_refusal,
    parse_what_if_scenario,
    sanitize_scenario_for_llm,
    trade_note_fallback,
)
from analysis_engine import run_analysis
from llm_chat import ask_general_llm, ask_llm, risk_policy_for_profile
from portfolio_store import add_trade, load_paper_portfolio, summarize_portfolio, update_cash_balance
from ticker_resolver import resolve_ticker
from watchlist_store import load_watchlist, save_watchlist


st.set_page_config(
    page_title="Agentic AI Stock Research & Trading Assistant",
    layout="wide",
)


CUSTOM_CSS = """
<style>
    .stApp {
        background: #0d1117;
        color: #f4f7fb;
    }
    [data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #273244;
    }
    .block-container {
        padding-top: 1.5rem;
    }
    .dashboard-card {
        background: #151c29;
        border: 1px solid #273244;
        border-radius: 8px;
        padding: 18px;
        height: 100%;
    }
    .hero-card {
        background: linear-gradient(135deg, #151c29 0%, #172233 100%);
        border: 1px solid #314158;
        border-radius: 8px;
        padding: 24px;
    }
    .metric-label {
        color: #9ca3af;
        font-size: 0.84rem;
        margin-bottom: 0.25rem;
    }
    .metric-value {
        color: #f9fafb;
        font-size: 1.45rem;
        font-weight: 700;
    }
    .small-note {
        color: #aeb8c7;
        font-size: 0.9rem;
    }
    .buy { color: #34d399; }
    .hold { color: #fbbf24; }
    .sell { color: #f87171; }
    .pill {
        display: inline-block;
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 0.8rem;
        font-weight: 700;
        border: 1px solid currentColor;
    }
    .fund-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px 18px;
        margin: 0.6rem 0 1rem 0;
    }
    .fund-cell {
        border-bottom: 1px solid #1f2937;
        padding: 6px 0 8px 0;
        min-width: 0;
    }
    .fund-label {
        color: #9ca3af;
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 0.2rem;
    }
    .fund-value {
        color: #f9fafb;
        font-size: 1.02rem;
        font-weight: 700;
        line-height: 1.2;
        overflow-wrap: anywhere;
    }
    .fund-section-title {
        color: #e5e7eb;
        font-size: 0.95rem;
        font-weight: 800;
        margin: 1rem 0 0.2rem 0;
    }
    @media (max-width: 1000px) {
        .fund-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
</style>
"""

FUNDAMENTALS_LLM_QUESTIONS = [
    "Explain this company's fundamental health in plain English.",
    "What are the strongest and weakest fundamentals?",
    "Is the valuation expensive compared with growth and profitability?",
    "What should I monitor before adding or holding this stock?",
]

SAMPLE_SCORE_NAMES = {"News Sentiment", "Event Risk"}


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    initialize_session_state()
    render_sidebar()

    analysis = st.session_state.analysis
    st.title("Agentic AI Stock Research & Trading Assistant")
    st.caption("Decision-support dashboard for stock research, portfolio risk, and paper trade simulation.")

    render_kpis(analysis)
    render_portfolio_narrative(analysis)
    render_recommendation_hero(analysis)
    render_action_buttons(analysis)
    render_tabs(analysis)


def initialize_session_state() -> None:
    defaults = {
        "ticker_input": "AAPL",
        "period_input": "1Y",
        "risk_profile_input": "Moderate",
        "trade_mode_input": "Paper Trading",
        "chat_mode_input": "Current Stock",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    if "analysis" not in st.session_state:
        st.session_state.analysis = run_analysis("AAPL", "1Y", "Moderate", "Paper Trading")
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("general_chat_history", [])
    st.session_state.setdefault("trade_ticket_side", "Buy")
    if "paper_portfolio" not in st.session_state:
        st.session_state.paper_portfolio = load_paper_portfolio()
        refresh_portfolio_summary()
    st.session_state.paper_trades = st.session_state.paper_portfolio["trades"]
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = load_watchlist()


def analyze_selected_stock() -> None:
    ticker_input = st.session_state.get("ticker_input", "AAPL")
    period = st.session_state.get("period_input", "1Y")
    risk_profile = st.session_state.get("risk_profile_input", "Moderate")
    trade_mode = st.session_state.get("trade_mode_input", "Paper Trading")

    resolved_ticker, source = resolve_ticker(ticker_input)
    st.session_state.selected_ticker = resolved_ticker
    st.session_state.ticker_input = resolved_ticker
    st.session_state.resolved_ticker_note = f"Resolved '{ticker_input}' to {resolved_ticker} using {source}."
    st.session_state.analysis = run_analysis(resolved_ticker, period, risk_profile, trade_mode)
    st.session_state.chat_history = []
    clear_stock_ai_outputs()
    clear_portfolio_ai_outputs()


def refresh_portfolio_summary() -> None:
    st.session_state.portfolio_summary = summarize_portfolio(st.session_state.paper_portfolio)


def refresh_current_analysis() -> None:
    final = st.session_state.get("analysis", {}).get("final_recommendation", {})
    ticker = final.get("ticker") or st.session_state.get("ticker_input", "AAPL")
    st.session_state.analysis = run_analysis(
        ticker,
        st.session_state.get("period_input", "1Y"),
        st.session_state.get("risk_profile_input", "Moderate"),
        st.session_state.get("trade_mode_input", "Paper Trading"),
    )


def clear_stock_ai_outputs() -> None:
    for key in (
        "ai_why_answer",
        "peer_comparison",
        "news_sentiment_explanation",
        "fundamentals_ai_question",
        "fundamentals_ai_answer",
    ):
        st.session_state.pop(key, None)


def clear_portfolio_ai_outputs() -> None:
    for key in ("portfolio_narrative", "what_if_result", "what_if_fallback_plan"):
        st.session_state.pop(key, None)


def analyze_ticker(ticker: str) -> None:
    st.session_state.ticker_input = ticker
    analyze_selected_stock()


def add_current_to_watchlist() -> None:
    final = st.session_state.analysis["final_recommendation"]
    ticker = final["ticker"]
    signal = final["recommendation"]

    if ticker in owned_tickers():
        st.session_state.watchlist_message = f"{ticker} is already in your portfolio. Use My Portfolio to analyze it."
        return

    updated_items = [
        item for item in st.session_state.watchlist if item["ticker"] != ticker
    ]
    updated_items.append({"ticker": ticker, "signal": signal})
    st.session_state.watchlist = updated_items
    save_watchlist(updated_items)
    st.session_state.watchlist_message = f"Added {ticker} to future watchlist."


def remove_from_watchlist(ticker: str) -> None:
    st.session_state.watchlist = [
        item for item in st.session_state.watchlist if item["ticker"] != ticker
    ]
    save_watchlist(st.session_state.watchlist)
    st.session_state.watchlist_message = f"Removed {ticker} from future watchlist."


def owned_tickers() -> set[str]:
    portfolio_summary = st.session_state.get("portfolio_summary", {})
    return {
        row["Ticker"]
        for row in portfolio_summary.get("positions", [])
        if float(row.get("Quantity", 0)) > 0
    }


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Stock Selection")
        st.text_input(
            "Ticker or Company Name",
            key="ticker_input",
            placeholder="Example: Walmart, PepsiCo, AAPL",
            on_change=analyze_selected_stock,
        )
        st.segmented_control("Time period", ["1M", "3M", "6M", "1Y"], key="period_input")
        st.selectbox("Risk profile", ["Conservative", "Moderate", "Aggressive"], key="risk_profile_input")
        st.radio("Trade mode", ["Paper Trading", "Research Only"], horizontal=False, key="trade_mode_input")
        st.button("Analyze", type="primary", width="stretch", on_click=analyze_selected_stock)
        st.caption("Type a company name and press Enter, or click Analyze after setting trade options.")

        if "resolved_ticker_note" in st.session_state:
            st.caption(st.session_state.resolved_ticker_note)

        st.divider()
        render_sidebar_portfolio()
        st.divider()
        render_sidebar_watchlist()

        st.divider()
        st.caption("sample data: News sentiment, event risk, backtesting, and seeded paper trades are demo data. Yahoo Finance powers price, profile, fundamentals, valuation, and portfolio-risk inputs.")


def render_sidebar_portfolio() -> None:
    st.subheader("My Portfolio")
    positions = st.session_state.get("portfolio_summary", {}).get("positions", [])

    if not positions:
        st.caption("No current holdings.")
        return

    for position in positions:
        ticker = position["Ticker"]
        quantity = float(position["Quantity"])
        row_left, row_right = st.columns([1.2, 1])
        row_left.markdown(f"**{ticker}**")
        row_left.caption(f"{quantity:,.4f} shares")
        row_right.button(
            "Analyze",
            key=f"portfolio_analyze_{ticker}",
            width="stretch",
            on_click=analyze_ticker,
            args=(ticker,),
        )


def render_sidebar_watchlist() -> None:
    st.subheader("Future Watchlist")
    owned = owned_tickers()
    future_items = future_watchlist_items(st.session_state.watchlist, owned)

    if not future_items:
        st.caption("No future watchlist ideas yet.")
        return

    for item in future_items:
        ticker = item["ticker"]
        signal = current_watchlist_signal(ticker)
        signal_class = signal.lower()
        row_left, row_right = st.columns([1.15, 1])
        row_left.markdown(
            f"**{ticker}** <span class='pill {signal_class}'>{signal}</span>",
            unsafe_allow_html=True,
        )
        row_right.button(
            "Analyze",
            key=f"watchlist_analyze_{ticker}",
            width="stretch",
            on_click=analyze_ticker,
            args=(ticker,),
        )
        row_right.button(
            "Remove",
            key=f"watchlist_remove_{ticker}",
            width="stretch",
            on_click=remove_from_watchlist,
            args=(ticker,),
        )


def current_watchlist_signal(ticker: str) -> str:
    try:
        analysis = run_analysis(
            ticker,
            st.session_state.get("period_input", "1Y"),
            st.session_state.get("risk_profile_input", "Moderate"),
            st.session_state.get("trade_mode_input", "Paper Trading"),
        )
    except Exception:
        return "Hold"
    return analysis["final_recommendation"]["recommendation"]


def render_kpis(analysis: dict) -> None:
    portfolio_summary = st.session_state.get("portfolio_summary", {})
    final = analysis["final_recommendation"]
    columns = st.columns(5)
    metrics = [
        ("Portfolio Value", f"${portfolio_summary.get('portfolio_value', 0):,.0f}"),
        ("Unrealized P&L", f"${portfolio_summary.get('unrealized_pnl', 0):,.0f}"),
        ("Cash Balance", f"${portfolio_summary.get('cash', 0):,.0f}"),
        ("Risk Level", analysis["portfolio"]["risk_level"]),
        ("AI Confidence", f"{final['confidence']}%"),
    ]
    for column, (label, value) in zip(columns, metrics):
        with column:
            st.markdown(f"<div class='dashboard-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>", unsafe_allow_html=True)
            if label == "Cash Balance":
                if st.button("Edit", key="edit_cash_balance", help="Manually set the paper cash balance."):
                    st.session_state.cash_editor_open = True

    cash_message = st.session_state.pop("cash_balance_message", None)
    if cash_message:
        st.success(cash_message)

    if st.session_state.get("cash_editor_open"):
        render_cash_balance_editor()


def render_cash_balance_editor() -> None:
    current_cash = current_cash_balance()
    default_cash = max(current_cash, 0.0)

    with st.form("cash_balance_editor_form"):
        st.caption("Manual cash update for the paper trading account. This changes only cash, not past trades.")
        new_cash_balance = st.number_input(
            "Cash balance",
            min_value=0.0,
            value=default_cash,
            step=100.0,
            format="%.2f",
        )
        save_col, cancel_col, _ = st.columns([1, 1, 6])
        save_clicked = save_col.form_submit_button("Save", type="primary")
        cancel_clicked = cancel_col.form_submit_button("Cancel")

    if cancel_clicked:
        st.session_state.cash_editor_open = False
        st.rerun()

    if save_clicked:
        st.session_state.paper_portfolio = update_cash_balance(
            st.session_state.paper_portfolio,
            new_cash_balance,
        )
        st.session_state.paper_trades = st.session_state.paper_portfolio.get("trades", [])
        refresh_portfolio_summary()
        refresh_current_analysis()
        clear_portfolio_ai_outputs()
        clear_trade_ticket_messages()
        st.session_state.cash_editor_open = False
        st.session_state.cash_balance_message = f"Cash balance updated to ${new_cash_balance:,.2f}."
        st.rerun()


def render_portfolio_narrative(analysis: dict) -> None:
    with st.expander("AI Portfolio Narrative", expanded=bool(st.session_state.get("portfolio_narrative"))):
        left, right = st.columns([3, 1])
        left.caption("Generate a short portfolio story using current holdings, cash, P&L, and the selected stock context.")
        if right.button("Generate Narrative", width="stretch"):
            with st.spinner("Writing portfolio narrative..."):
                st.session_state.portfolio_narrative = generate_portfolio_narrative(analysis)

        if st.session_state.get("portfolio_narrative"):
            st.write(st.session_state.portfolio_narrative)
        else:
            st.caption("No narrative generated yet.")


def generate_portfolio_narrative(analysis: dict) -> str:
    context = build_general_chat_context(analysis)
    context["feature_request"] = {
        "name": "AI Portfolio Narrative",
        "instruction": (
            "Write one concise paragraph using only portfolio_summary and current_recommendation. "
            "Cover portfolio health, concentration risk, biggest visible driver, and one practical "
            "paper-trading research step. Apply the selected risk_profile and risk_policy. "
            "Do not invent holdings, sectors, prices, or performance."
        ),
    }
    return ask_general_llm(
        "Task: Write the AI Portfolio Narrative from the provided context. "
        "Output format: one paragraph, 4-6 sentences. "
        "Rules: use exact supplied portfolio numbers when mentioned; adapt the conclusion to the selected risk profile; "
        "call out missing data instead of guessing.",
        context,
        [],
    )


def render_recommendation_hero(analysis: dict) -> None:
    final = analysis["final_recommendation"]
    recommendation = final["recommendation"]
    recommendation_class = recommendation.lower()
    st.markdown("")
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="small-note">{final['ticker']} - {final['company']}</div>
            <h1 class="{recommendation_class}" style="margin: 0.2rem 0;">{recommendation.upper()}</h1>
            <h3 style="margin-top: 0;">Confidence Score: {final['confidence']}%</h3>
            <p><b>Suggested Action:</b> {final['suggested_action']}</p>
            <p><b>AI Reasoning:</b> {final['reasoning']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_action_buttons(analysis: dict) -> None:
    st.markdown("")
    watch_col, compare_col, why_col = st.columns(3)

    if watch_col.button("Add to Watchlist", width="stretch", on_click=add_current_to_watchlist):
        pass

    if "watchlist_message" in st.session_state:
        st.info(st.session_state.watchlist_message)

    if why_col.button("Ask AI Why?", width="stretch"):
        with st.spinner("Asking the configured LLM..."):
            answer = ask_llm(
                "Task: Explain why the dashboard produced this recommendation. "
                "Output format: five short bullets: Final Call, Main Positive, Main Risk, Score Drivers, What To Monitor. "
                "Rules: use only supplied scores and summaries; interpret the recommendation through the selected risk profile; "
                "do not add outside news, price targets, or analyst views.",
                analysis,
                st.session_state.chat_history,
            )
        st.session_state.ai_why_answer = answer
        st.session_state.chat_history.append(("assistant", answer))

    if compare_col.button("Compare Peers", width="stretch"):
        with st.spinner("Comparing peer candidates..."):
            st.session_state.peer_comparison = generate_peer_comparison(analysis)

    if "ai_why_answer" in st.session_state:
        with st.expander("AI Explanation", expanded=True):
            st.write(st.session_state.ai_why_answer)
            st.caption("This answer is also saved in the Current Stock AI Chat history.")

    if "peer_comparison" in st.session_state:
        with st.expander("AI Comparative Analysis", expanded=True):
            st.write(st.session_state.peer_comparison)

    render_trade_ticket(analysis)


def generate_peer_comparison(analysis: dict) -> str:
    context = build_peer_comparison_context(
        analysis,
        st.session_state.get("period_input", "1Y"),
        st.session_state.get("risk_profile_input", "Moderate"),
        st.session_state.get("trade_mode_input", "Paper Trading"),
    )
    return ask_general_llm(
        "Task: Compare the selected stock against the listed peer candidates. "
        "Output format: Selected Stock, Peer Snapshot, Strongest Candidate, Key Tradeoff, What To Monitor. "
        "Rules: choose only from the selected and peer tickers in the context; rank the tradeoff for the selected risk profile; "
        "do not invent new peers, prices, news, or metrics. "
        "If the data is too close to call, say that clearly instead of forcing a winner.",
        context,
        [],
    )


def render_trade_ticket(analysis: dict) -> None:
    if analysis["portfolio"]["trade_mode"] == "Research Only":
        st.caption("Paper trade simulator is disabled in Research Only mode.")
        return

    final = analysis["final_recommendation"]
    valuation = analysis["valuation"]
    portfolio_risk = analysis["portfolio_risk"]
    ticker = final["ticker"]
    current_price = float(valuation["current_price"])

    with st.expander("Paper Trade Ticket", expanded=True):
        render_trade_ticket_messages()
        side = st.radio(
            "Trade side",
            ["Buy", "Sell"],
            key="trade_ticket_side",
            horizontal=True,
        )

        if side == "Buy":
            render_buy_ticket(ticker, current_price, portfolio_risk["suggested_position_size"])
        else:
            render_sell_ticket(ticker, current_price)


def render_trade_ticket_messages() -> None:
    if st.session_state.get("trade_ticket_success"):
        st.success(st.session_state.trade_ticket_success)
    if st.session_state.get("trade_ticket_error"):
        st.error(st.session_state.trade_ticket_error)
    if st.session_state.get("latest_trade_note"):
        st.info(st.session_state.latest_trade_note)


def render_buy_ticket(ticker: str, current_price: float, suggested_amount: int) -> None:
    cash_balance = current_cash_balance()
    st.caption(f"Cash balance available for paper buys: ${cash_balance:,.2f}.")

    input_mode = st.radio(
        "Buy input",
        ["Enter dollar amount", "Enter quantity"],
        horizontal=True,
        key="buy_input_mode",
    )

    if input_mode == "Enter dollar amount":
        default_amount = default_buy_amount(suggested_amount, cash_balance)
        amount = st.number_input(
            "Dollar amount to invest",
            min_value=0.0,
            value=default_amount,
            step=100.0,
            format="%.2f",
        )
        quantity = amount / current_price if current_price else 0.0
        trade_value = amount
    else:
        quantity = st.number_input(
            "Quantity to buy",
            min_value=0.0,
            value=1.0,
            step=1.0,
            format="%.4f",
        )
        trade_value = quantity * current_price

    st.caption(f"Estimated buy: {quantity:,.4f} shares of {ticker} at ${current_price:,.2f}, value ${trade_value:,.2f}.")

    if st.button("Add Buy Simulation", type="primary", width="stretch"):
        clear_trade_ticket_messages()
        if quantity <= 0 or trade_value <= 0:
            st.session_state.trade_ticket_error = "Enter a quantity or dollar amount greater than zero."
            st.rerun()
        if trade_value > cash_balance:
            st.session_state.trade_ticket_error = (
                f"Buy rejected. Trade value ${trade_value:,.2f} is greater than "
                f"cash balance ${cash_balance:,.2f}."
            )
            st.rerun()
        if add_paper_trade(ticker, "Buy", quantity, current_price, trade_value, input_mode):
            st.session_state.trade_ticket_success = (
                f"Added paper buy for {quantity:,.4f} shares of {ticker}. "
                f"Cash balance reduced by ${trade_value:,.2f}."
            )
            st.rerun()
        st.session_state.trade_ticket_error = "Buy rejected. Check quantity, trade value, and cash balance."
        st.rerun()


def render_sell_ticket(ticker: str, current_price: float) -> None:
    holding_quantity = current_holding_quantity(ticker)
    st.caption(f"Current paper holding for {ticker}: {holding_quantity:,.4f} shares.")

    quantity = st.number_input(
        "Quantity to sell",
        min_value=0.0,
        value=1.0,
        step=1.0,
        format="%.4f",
    )
    trade_value = quantity * current_price

    st.caption(f"Estimated sell: {quantity:,.4f} shares of {ticker} at ${current_price:,.2f}, value ${trade_value:,.2f}.")

    if st.button("Add Sell Simulation", type="primary", width="stretch"):
        clear_trade_ticket_messages()
        if quantity <= 0 or trade_value <= 0:
            st.session_state.trade_ticket_error = "Enter a quantity greater than zero."
            st.rerun()
        if quantity > holding_quantity:
            st.session_state.trade_ticket_error = (
                f"Sell rejected. You entered {quantity:,.4f} shares, but the current "
                f"paper holding is {holding_quantity:,.4f} shares."
            )
            st.rerun()
        if add_paper_trade(ticker, "Sell", quantity, current_price, trade_value, "Enter quantity"):
            st.session_state.trade_ticket_success = (
                f"Added paper sell for {quantity:,.4f} shares of {ticker}. "
                f"Cash balance increased by ${trade_value:,.2f}."
            )
            st.rerun()
        st.session_state.trade_ticket_error = "Sell rejected. Check quantity and current paper holding."
        st.rerun()


def clear_trade_ticket_messages() -> None:
    st.session_state.pop("trade_ticket_success", None)
    st.session_state.pop("trade_ticket_error", None)
    st.session_state.pop("latest_trade_note", None)


def current_cash_balance() -> float:
    portfolio_summary = st.session_state.get("portfolio_summary", {})
    return float(portfolio_summary.get("cash", 0))


def current_holding_quantity(ticker: str) -> float:
    positions = st.session_state.get("portfolio_summary", {}).get("positions", [])
    for position in positions:
        if str(position.get("Ticker", "")).upper() == ticker.upper():
            return float(position.get("Quantity", 0))
    return 0.0


def default_buy_amount(suggested_amount: int, cash_balance: float) -> float:
    if cash_balance <= 0:
        return 0.0
    return float(min(max(suggested_amount, 1000), cash_balance))


def add_paper_trade(
    ticker: str,
    action: str,
    quantity: float,
    price: float,
    trade_value: float,
    input_mode: str,
) -> bool:
    if quantity <= 0 or trade_value <= 0:
        return False
    if action == "Buy" and trade_value > current_cash_balance() + 0.005:
        return False
    if action == "Sell" and quantity > current_holding_quantity(ticker) + 0.0001:
        return False

    trade = {
        "ticker": ticker,
        "action": action,
        "input_mode": input_mode,
        "quantity": quantity,
        "price": price,
        "trade_value": trade_value,
    }
    with st.spinner("Writing AI trade journal note..."):
        trade["trade_note"] = generate_trade_journal_note(trade, st.session_state.analysis)

    st.session_state.paper_portfolio = add_trade(
        st.session_state.paper_portfolio,
        trade,
    )
    st.session_state.latest_trade_note = trade["trade_note"]
    st.session_state.paper_trades = st.session_state.paper_portfolio["trades"]
    refresh_portfolio_summary()
    clear_portfolio_ai_outputs()
    if action == "Buy":
        remove_owned_tickers_from_watchlist()
    return True


def generate_trade_journal_note(trade: dict, analysis: dict) -> str:
    question = (
        "Task: Write one paper-trade journal note for this simulated trade. "
        f"Trade: {trade['action']} {trade['quantity']:,.4f} shares of {trade['ticker']} "
        f"at ${trade['price']:,.2f}, trade value ${trade['trade_value']:,.2f}, "
        f"input mode: {trade['input_mode']}. "
        "Output format: 2-3 sentences covering setup, reason, and follow-up check. "
        "Rules: use only the current dashboard context; explain whether the trade size fits the selected risk profile; "
        "do not claim real execution, real account activity, "
        "future return, or external market news."
    )
    note = ask_llm(question, analysis, [])
    if note.startswith("I could not reach") or note.startswith("The LLM returned"):
        return trade_note_fallback(trade, analysis)
    return note


def remove_owned_tickers_from_watchlist() -> None:
    owned = owned_tickers()
    if not owned:
        return

    updated_items = [
        item for item in st.session_state.watchlist if item["ticker"] not in owned
    ]
    if len(updated_items) != len(st.session_state.watchlist):
        st.session_state.watchlist = updated_items
        save_watchlist(updated_items)


def render_tabs(analysis: dict) -> None:
    tabs = st.tabs(
        [
            "Overview",
            "Technical Analysis",
            "Fundamentals",
            "News Sentiment",
            "Valuation",
            "Portfolio Risk",
            "Backtesting",
            "AI Chat",
        ]
    )
    with tabs[0]:
        render_overview_tab(analysis)
    with tabs[1]:
        render_technical_tab(analysis)
    with tabs[2]:
        render_fundamentals_tab(analysis)
    with tabs[3]:
        render_news_tab(analysis)
    with tabs[4]:
        render_valuation_tab(analysis)
    with tabs[5]:
        render_portfolio_tab(analysis)
    with tabs[6]:
        render_backtesting_tab(analysis)
    with tabs[7]:
        render_chat_tab(analysis)


def render_overview_tab(analysis: dict) -> None:
    left, right = st.columns([1.6, 1])
    with left:
        st.subheader("Price Chart")
        chart_data = analysis["price_history"].set_index("Date")[["Close", "MA50", "MA200"]]
        st.line_chart(chart_data)
        render_price_source_caption(analysis)
    with right:
        st.subheader("Agent Score Breakdown")
        for name, score in analysis["final_recommendation"]["score_breakdown"].items():
            label = f"{name}: {score}"
            if name in SAMPLE_SCORE_NAMES:
                label = f"{label} | sample data"
            st.progress(score, text=label)
        st.warning(analysis["portfolio_risk"]["warning"])

    st.subheader("Key Risks")
    for warning in analysis["final_recommendation"]["risk_warnings"]:
        st.write(f"- {warning}")


def render_technical_tab(analysis: dict) -> None:
    technical = analysis["technical"]
    st.subheader("Technical Agent View")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Technical Score", technical["score"])
    col2.metric("Signal", technical["signal"])
    col3.metric("RSI", technical["rsi"])
    col4.metric("MACD", technical["macd"])
    st.line_chart(analysis["price_history"].set_index("Date")[["Close", "MA50", "MA200"]])
    render_price_source_caption(analysis)
    st.info(technical["summary"])
    st.dataframe(
        analysis["price_history"][["Date", "Close", "MA50", "MA200", "Volume"]].tail(12),
        width="stretch",
        hide_index=True,
    )


def render_price_source_caption(analysis: dict) -> None:
    source = analysis.get("price_source", {})
    data_source = source.get("data_source", "Price source unavailable")
    as_of = source.get("as_of", "N/A")
    source_note = source.get("source_note", "")
    st.caption(f"Price source: {data_source} | As of {as_of}. {source_note}")


def render_sample_data_label(note: str) -> None:
    st.caption(f"sample data: {note}")


def render_fundamentals_tab(analysis: dict) -> None:
    fundamentals = analysis["fundamentals"]
    st.subheader("Fundamentals Agent View")

    if fundamentals.get("is_live"):
        st.caption(f"Source: {fundamentals['data_source']} | As of {fundamentals['as_of']}")
    else:
        st.warning(fundamentals.get("source_note", "Using fallback fundamentals."))

    render_compact_metric_grid("Scale & Growth", [
        ("Market Cap", fundamentals.get("market_cap", "N/A")),
        ("Revenue", fundamentals.get("total_revenue", "N/A")),
        ("Gross Profit", fundamentals.get("gross_profit", "N/A")),
        ("Net Income", fundamentals.get("net_income", "N/A")),
        ("Revenue Growth", fundamentals["revenue_growth"]),
        ("EPS Growth", fundamentals["eps_growth"]),
        ("Earnings Growth", fundamentals.get("earnings_growth", "N/A")),
        ("Shares Outstanding", fundamentals.get("shares_outstanding", "N/A")),
    ])

    render_compact_metric_grid("Profitability & Cash Flow", [
        ("Profit Margin", fundamentals["profit_margin"]),
        ("Operating Margin", fundamentals.get("operating_margin", "N/A")),
        ("Gross Margin", fundamentals.get("gross_margin", "N/A")),
        ("EBITDA Margin", fundamentals.get("ebitda_margin", "N/A")),
        ("Return on Equity", fundamentals.get("return_on_equity", "N/A")),
        ("Operating Cash Flow", fundamentals.get("operating_cash_flow", "N/A")),
        ("Free Cash Flow", fundamentals["free_cash_flow"]),
        ("EBITDA", fundamentals.get("ebitda", "N/A")),
    ])

    render_compact_metric_grid("Valuation & Multiples", [
        ("PE Ratio", fundamentals["pe_ratio"]),
        ("Forward PE", fundamentals.get("forward_pe", "N/A")),
        ("PEG Ratio", fundamentals.get("peg_ratio", "N/A")),
        ("Price / Sales", fundamentals.get("price_to_sales", "N/A")),
        ("Price / Book", fundamentals.get("price_to_book", "N/A")),
        ("EV / Revenue", fundamentals.get("enterprise_to_revenue", "N/A")),
        ("EV / EBITDA", fundamentals.get("enterprise_to_ebitda", "N/A")),
        ("Enterprise Value", fundamentals.get("enterprise_value", "N/A")),
    ])

    render_compact_metric_grid("Balance Sheet & Per Share", [
        ("Debt to Equity", fundamentals["debt_to_equity"]),
        ("Current Ratio", fundamentals.get("current_ratio", "N/A")),
        ("Quick Ratio", fundamentals.get("quick_ratio", "N/A")),
        ("Total Cash", fundamentals.get("total_cash", "N/A")),
        ("Total Debt", fundamentals.get("total_debt", "N/A")),
        ("Cash / Share", fundamentals.get("total_cash_per_share", "N/A")),
        ("Book Value / Share", fundamentals.get("book_value", "N/A")),
        ("Revenue / Share", fundamentals.get("revenue_per_share", "N/A")),
    ])

    render_compact_metric_grid("Market Risk & Shareholder Return", [
        ("Trailing EPS", fundamentals.get("trailing_eps", "N/A")),
        ("Forward EPS", fundamentals.get("forward_eps", "N/A")),
        ("Beta", fundamentals.get("beta", "N/A")),
        ("Dividend Yield", fundamentals.get("dividend_yield", "N/A")),
        ("Payout Ratio", fundamentals.get("payout_ratio", "N/A")),
    ])

    st.success(f"Signal: {fundamentals['signal']} with score {fundamentals['score']}.")
    st.write(f"Strengths: {fundamentals.get('strengths', 'N/A')}.")
    st.write(f"Weaknesses: {fundamentals.get('weaknesses', 'N/A')}.")

    render_fundamentals_llm_explainer(analysis)

    st.subheader("Company Details")
    st.dataframe(
        [
            {"Field": "Company", "Value": fundamentals.get("company", "N/A")},
            {"Field": "Sector", "Value": fundamentals.get("sector", "N/A")},
            {"Field": "Industry", "Value": fundamentals.get("industry", "N/A")},
            {"Field": "Website", "Value": fundamentals.get("website", "N/A")},
            {"Field": "Data Source", "Value": fundamentals.get("data_source", "N/A")},
            {"Field": "As Of", "Value": fundamentals.get("as_of", "N/A")},
        ],
        width="stretch",
        hide_index=True,
    )


def render_fundamentals_llm_explainer(analysis: dict) -> None:
    final = analysis["final_recommendation"]

    st.subheader("Ask LLM About Fundamentals")
    st.caption(
        f"These questions use only the fundamentals already loaded for {final['ticker']}."
    )

    cols = st.columns(2)
    for index, question in enumerate(FUNDAMENTALS_LLM_QUESTIONS):
        if cols[index % 2].button(question, key=f"fundamentals_llm_{index}", width="stretch"):
            ask_fundamentals_question(question, analysis)

    custom_question = st.text_input(
        "Custom fundamentals question",
        key="fundamentals_custom_question",
        placeholder="Example: Is this company financially strong enough for a long-term watchlist?",
    )
    if st.button("Ask Fundamentals LLM", width="stretch"):
        if custom_question.strip():
            ask_fundamentals_question(custom_question.strip(), analysis)
        else:
            st.warning("Enter a fundamentals question first.")

    if st.session_state.get("fundamentals_ai_answer"):
        with st.expander("AI Fundamentals Explanation", expanded=True):
            st.caption(st.session_state.get("fundamentals_ai_question", "Fundamentals question"))
            st.write(st.session_state.fundamentals_ai_answer)


def ask_fundamentals_question(question: str, analysis: dict) -> None:
    prompt = (
        "Task: Explain the Fundamentals tab for the selected ticker. "
        "Allowed data: dashboard fundamentals, recommendation, risk profile, and score context already provided. "
        "Output format: five short bullets with labels: Quality, Growth, Profitability, Balance Sheet, Watch Next. "
        "Rules: adapt Watch Next to the selected risk profile; do not invent ratios, prices, forecasts, headlines, analyst opinions, or missing values. "
        "If a metric is N/A or unavailable, say it is unavailable. "
        f"User question: {question}"
    )
    with st.spinner("Asking the configured LLM about fundamentals..."):
        st.session_state.fundamentals_ai_question = question
        st.session_state.fundamentals_ai_answer = ask_llm(prompt, analysis, [])


def render_compact_metric_grid(title: str, metric_pairs: list[tuple[str, object]]) -> None:
    cells = []
    for label, value in metric_pairs:
        cells.append(
            "<div class='fund-cell'>"
            f"<div class='fund-label'>{escape(str(label))}</div>"
            f"<div class='fund-value'>{escape(str(value))}</div>"
            "</div>"
        )

    st.markdown(
        f"<div class='fund-section-title'>{escape(title)}</div>"
        f"<div class='fund-grid'>{''.join(cells)}</div>",
        unsafe_allow_html=True,
    )


def render_news_tab(analysis: dict) -> None:
    news = analysis["news"]
    st.subheader("News Sentiment Agent View")
    render_sample_data_label("News sentiment score, themes, and headlines are simulated.")
    col1, col2 = st.columns([1, 2])
    col1.metric("Sentiment Score", news["score"])
    col1.metric("Sentiment", news["signal"])
    col2.info(news["summary"])
    st.write("Main Drivers")
    st.write(", ".join(news["themes"]))
    pos, neg = st.columns(2)
    pos.write("Positive Headlines")
    for headline in news["positive_headlines"]:
        pos.success(headline)
    neg.write("Risk Headlines")
    for headline in news["negative_headlines"]:
        neg.warning(headline)

    if st.button("Explain This Sentiment", width="stretch"):
        with st.spinner("Explaining news sentiment..."):
            st.session_state.news_sentiment_explanation = ask_llm(
                "Task: Explain the current news sentiment. "
                "Allowed data: score, signal, themes, positive headlines, and risk headlines from the dashboard. "
                "Output format: exactly three bullets: Overall Read, Positive Drivers, Risk Drivers. "
                "Rules: explain how the sentiment matters for the selected risk profile; "
                "do not invent new headlines, dates, publishers, events, or analyst commentary.",
                analysis,
                [],
            )

    if st.session_state.get("news_sentiment_explanation"):
        with st.expander("AI News Sentiment Explainer", expanded=True):
            st.write(st.session_state.news_sentiment_explanation)


def render_valuation_tab(analysis: dict) -> None:
    valuation = analysis["valuation"]
    st.subheader("Valuation Agent View")
    cols = st.columns(4)
    cols[0].metric("Valuation Score", valuation["score"])
    cols[1].metric("Signal", valuation["signal"])
    cols[2].metric("Current Price", f"${valuation['current_price']:,.2f}")
    cols[3].metric("FCF Yield", valuation.get("fcf_yield", "N/A"))
    st.caption(valuation.get("source_note", "Valuation uses loaded fundamentals."))
    st.dataframe(
        [
            {"Metric": "PE Ratio", "Value": str(valuation.get("pe_ratio", "N/A"))},
            {"Metric": "Forward PE", "Value": str(valuation.get("forward_pe", "N/A"))},
            {"Metric": "PEG Ratio", "Value": str(valuation.get("peg_ratio", "N/A"))},
            {"Metric": "Price / Sales", "Value": str(valuation.get("price_to_sales", "N/A"))},
            {"Metric": "Price / Book", "Value": str(valuation.get("price_to_book", "N/A"))},
            {"Metric": "EV / Revenue", "Value": str(valuation.get("enterprise_to_revenue", "N/A"))},
            {"Metric": "EV / EBITDA", "Value": str(valuation.get("enterprise_to_ebitda", "N/A"))},
            {"Metric": "Free Cash Flow Yield", "Value": str(valuation.get("fcf_yield", "N/A"))},
        ],
        width="stretch",
        hide_index=True,
    )
    for note in valuation.get("valuation_notes", []):
        st.write(f"- {note}")


def render_portfolio_tab(analysis: dict) -> None:
    risk = analysis["portfolio_risk"]
    portfolio_summary = st.session_state.get("portfolio_summary", {})
    st.subheader("Portfolio Risk Agent View")
    cols = st.columns(4)
    cols[0].metric("Portfolio Fit Score", risk["score"])
    cols[1].metric("Sector", risk["sector"])
    cols[2].metric("Current Exposure", f"{risk['current_sector_exposure']}%")
    cols[3].metric("Post Trade", f"{risk['post_trade_exposure']}%")
    st.caption(risk.get("data_source", "Portfolio risk uses current paper portfolio holdings."))
    st.warning(risk["warning"])
    st.bar_chart(
        {
            "Current": [risk["current_sector_exposure"], 100 - risk["current_sector_exposure"]],
            "Post Trade": [risk["post_trade_exposure"], 100 - risk["post_trade_exposure"]],
        }
    )

    st.subheader("Simulated Holdings")
    render_sample_data_label("Holdings come from the seeded paper portfolio until you add your own paper trades.")
    holdings = portfolio_summary.get("positions", [])
    if holdings:
        st.dataframe(holdings, width="stretch", hide_index=True)
    else:
        st.caption("No simulated holdings yet.")

    render_what_if_simulator(analysis, portfolio_summary)

    st.subheader("Paper Trade History")
    render_sample_data_label("Seeded historical buys are sample data; new trades you add are paper-trade records.")
    if st.session_state.paper_trades:
        st.dataframe(st.session_state.paper_trades, width="stretch", hide_index=True)
    else:
        st.caption("No paper trades yet.")


def render_what_if_simulator(analysis: dict, portfolio_summary: dict) -> None:
    st.subheader("AI What-If Scenario")
    st.caption("Examples: 'NVDA drops 20%', 'portfolio drops 15%', 'AAPL rises 10%', or 'sell 50% of AAPL'.")
    scenario_text = st.text_input(
        "Scenario",
        key="what_if_input",
        placeholder="What happens if NVDA drops 20%?",
    )

    if st.button("Run What-If Scenario", width="stretch"):
        positions = portfolio_summary.get("positions", [])
        selected_ticker = analysis["final_recommendation"]["ticker"]
        parsed = parse_what_if_scenario(scenario_text, selected_ticker, positions)
        impact = calculate_what_if_impact(
            parsed,
            positions,
            float(portfolio_summary.get("portfolio_value", 0)),
        )
        st.session_state.pop("what_if_fallback_plan", None)
        if "error" in impact:
            st.session_state.what_if_result = impact
        else:
            with st.spinner("Explaining scenario impact..."):
                impact["ai_explanation"] = generate_what_if_explanation(impact, portfolio_summary)
            st.session_state.what_if_result = impact

    result = st.session_state.get("what_if_result")
    if not result:
        return

    if "error" in result:
        st.warning(result["error"])
        return

    cols = st.columns(3)
    if result.get("scenario_type") == "position_reduction":
        cols[0].metric("Cash Generated", f"${result['cash_generated']:,.2f}")
        cols[1].metric("Portfolio Before", f"${result['portfolio_value_before']:,.2f}")
        cols[2].metric("Portfolio After", f"${result['portfolio_value_after']:,.2f}")
        st.caption(result["note"])
    else:
        cols[0].metric("Dollar Impact", f"${result['total_dollar_impact']:,.2f}")
        cols[1].metric("Portfolio Before", f"${result['portfolio_value_before']:,.2f}")
        cols[2].metric("Portfolio After", f"${result['portfolio_value_after']:,.2f}")
    st.dataframe(result["affected_positions"], width="stretch", hide_index=True)
    st.info(result["ai_explanation"])

    if st.button("Suggest Fallback Plan", width="stretch"):
        with st.spinner("Building fallback plan..."):
            st.session_state.what_if_fallback_plan = generate_fallback_plan(
                analysis,
                result,
                portfolio_summary,
            )

    if st.session_state.get("what_if_fallback_plan"):
        with st.expander("AI Fallback Plan", expanded=True):
            st.write(st.session_state.what_if_fallback_plan)


def generate_what_if_explanation(impact: dict, portfolio_summary: dict) -> str:
    safe_impact = sanitize_scenario_for_llm(impact)
    context = {
        "feature_request": "Explain a Python-calculated hypothetical paper-trading scenario.",
        "risk_policy": risk_policy_for_profile(st.session_state.get("risk_profile_input", "Moderate")),
        "scenario_impact": safe_impact,
        "portfolio_summary": portfolio_summary,
    }
    answer = ask_general_llm(
        "Task: Explain the Python-calculated hypothetical scenario mechanics in plain English. "
        "Output format: What changed, Portfolio impact, Interpretation, Risk-management takeaway. "
        "Rules: use only scenario_impact and portfolio_summary; do not advise the user to buy or sell; "
        "make the risk-management takeaway match the selected risk profile; "
        "do not invent taxes, fees, slippage, or price moves not shown in the scenario.",
        context,
        [],
    )
    if looks_like_llm_refusal(answer):
        return local_what_if_explanation(impact)
    return answer


def generate_fallback_plan(
    analysis: dict,
    scenario_impact: dict,
    portfolio_summary: dict,
) -> str:
    future_items = future_watchlist_items(
        st.session_state.get("watchlist", []),
        owned_tickers(),
    )
    context = build_fallback_plan_context(
        analysis,
        sanitize_scenario_for_llm(scenario_impact),
        portfolio_summary,
        future_items,
        st.session_state.get("period_input", "1Y"),
        st.session_state.get("risk_profile_input", "Moderate"),
        st.session_state.get("trade_mode_input", "Paper Trading"),
    )
    return ask_general_llm(
        "Task: Suggest a paper-trading fallback plan after this what-if scenario. "
        "Output format: Defensive Action, Alternative Stock To Research, Why This Alternative, What To Monitor Next. "
        "Rules: choose alternatives only from peer_candidates or future_watchlist_candidates; "
        "adapt the fallback plan to the selected risk profile and risk policy; "
        "do not invent tickers, prices, news, or metrics; make it clear this is research support, not personal advice.",
        context,
        [],
    )


def render_backtesting_tab(analysis: dict) -> None:
    backtest = analysis["backtest"]
    st.subheader("Backtesting Agent View")
    render_sample_data_label("Backtesting metrics and trade rows are simulated sample data.")
    cols = st.columns(4)
    cols[0].metric("Total Return", f"{backtest['total_return']}%")
    cols[1].metric("Win Rate", f"{backtest['win_rate']}%")
    cols[2].metric("Max Drawdown", f"{backtest['max_drawdown']}%")
    cols[3].metric("Trades", backtest["trades"])
    st.dataframe(backtest["history"], width="stretch", hide_index=True)


def render_chat_tab(analysis: dict) -> None:
    st.subheader("AI Chat")
    final = analysis["final_recommendation"]
    chat_mode = st.segmented_control(
        "Chat mode",
        ["Current Stock", "General Assistant"],
        key="chat_mode_input",
    )

    if chat_mode == "Current Stock":
        st.caption(
            f"Ask about {final['ticker']}, the current recommendation, scores, valuation, risk, and paper trading."
        )
        history_key = "chat_history"
        placeholder = f"Ask about {final['ticker']} or the current recommendation"
        suggestions = [
            "Why is this the recommendation?",
            "What is the biggest risk?",
            "Should I simulate a buy or wait?",
        ]
    else:
        st.caption("Ask about the app, watchlist, portfolio simulation, investing concepts, or hackathon demo flow.")
        history_key = "general_chat_history"
        placeholder = "Ask about the app, portfolio, watchlist, or investing concepts"
        suggestions = [
            "How should I use this app in a hackathon demo?",
            "Explain paper trading in simple terms.",
            "How can I compare stocks in my watchlist?",
        ]

    render_suggested_chat_questions(suggestions, chat_mode, analysis)

    for role, message in st.session_state[history_key]:
        with st.chat_message(role):
            st.write(message)

    question = st.chat_input(placeholder)
    if question:
        answer_chat_question(question, chat_mode, analysis)
        st.rerun()


def render_suggested_chat_questions(
    suggestions: list[str],
    chat_mode: str,
    analysis: dict,
) -> None:
    cols = st.columns(len(suggestions))
    for index, suggestion in enumerate(suggestions):
        if cols[index].button(suggestion, key=f"{chat_mode}_{index}", width="stretch"):
            answer_chat_question(suggestion, chat_mode, analysis)
            st.rerun()


def answer_chat_question(question: str, chat_mode: str, analysis: dict) -> None:
    if chat_mode == "Current Stock":
        history = st.session_state.chat_history
        history.append(("user", question))
        with st.spinner("Asking the configured LLM..."):
            answer = ask_llm(question, analysis, history[:-1])
        history.append(("assistant", answer))
        return

    history = st.session_state.general_chat_history
    history.append(("user", question))
    with st.spinner("Asking the configured LLM..."):
        answer = ask_general_llm(question, build_general_chat_context(analysis), history[:-1])
    history.append(("assistant", answer))


def build_general_chat_context(analysis: dict) -> dict:
    final = analysis["final_recommendation"]
    portfolio_summary = st.session_state.get("portfolio_summary", {})
    risk_profile = st.session_state.get("risk_profile_input")

    return {
        "app_name": "Agentic AI Stock Research & Trading Assistant",
        "app_capabilities": [
            "ticker or company-name lookup",
            "watchlist",
            "technical analysis",
            "fundamentals",
            "news sentiment",
            "valuation",
            "portfolio risk",
            "backtesting",
            "paper trade simulation",
        ],
        "current_inputs": {
            "selected_ticker": final["ticker"],
            "selected_company": final["company"],
            "period": st.session_state.get("period_input"),
            "risk_profile": risk_profile,
            "trade_mode": st.session_state.get("trade_mode_input"),
        },
        "risk_policy": risk_policy_for_profile(risk_profile),
        "future_watchlist": future_watchlist_items(
            st.session_state.get("watchlist", []),
            owned_tickers(),
        ),
        "portfolio_summary": {
            "portfolio_value": portfolio_summary.get("portfolio_value"),
            "unrealized_pnl": portfolio_summary.get("unrealized_pnl"),
            "cash": portfolio_summary.get("cash"),
            "positions": portfolio_summary.get("positions", []),
        },
        "current_recommendation": {
            "recommendation": final["recommendation"],
            "confidence": final["confidence"],
            "score_breakdown": final["score_breakdown"],
        },
    }


if __name__ == "__main__":
    main()
