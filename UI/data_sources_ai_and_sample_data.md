# Data Sources, AI Usage, and Sample Data

This document explains what parts of the Streamlit stock research app use live market data, Python calculations, LLM responses, and sample/demo data.

## Summary

The app follows this pattern:

- Yahoo Finance provides market, company, and fundamentals data.
- Python calculates technical indicators, valuation scores, portfolio risk, paper-trade impact, and what-if scenarios.
- The LLM explains the data already available in the app.
- News sentiment, event risk, backtesting, and seeded paper trades remain sample data and are labeled in the UI.

## Real Data From Yahoo Finance

| App Area | Source | Notes |
|---|---|---|
| Ticker/company lookup | Yahoo Finance search through `yfinance` | Used when a user enters a company name like `Walmart`, `PepsiCo`, or `FedEx`. |
| Price chart | Yahoo Finance daily price history | Used for charting close price, volume, MA50, MA200, and daily return. |
| Technical indicators | Python calculations on Yahoo price data | RSI, moving averages, daily return, and technical score are calculated locally. |
| Company profile | Yahoo Finance company info | Company name, sector, industry, exchange, currency, market cap, and beta. |
| Fundamentals | Yahoo Finance fundamentals | Revenue, margins, PE, debt, cash, free cash flow, EPS, and related values. |
| Valuation inputs | Yahoo Finance fundamentals | PE, forward PE, PEG, price/sales, price/book, EV/revenue, EV/EBITDA, and free-cash-flow yield. |
| Portfolio current prices | Yahoo Finance latest price history | Used to estimate current market value of paper holdings. |
| Portfolio sector data | Yahoo Finance company profile | Used to calculate portfolio sector exposure. |

Relevant files:

- `UI/ticker_resolver.py`
- `UI/price_history_fetcher.py`
- `UI/company_profile_fetcher.py`
- `UI/fundamentals_fetcher.py`
- `UI/portfolio_store.py`
- `UI/analysis_engine.py`

## Python Calculations

Python is responsible for calculating numbers. The LLM is not used for financial math.

| Calculation | Where It Happens | Notes |
|---|---|---|
| Moving averages | `UI/price_history_fetcher.py` | MA50 and MA200 are calculated from Yahoo close prices. |
| Daily returns | `UI/price_history_fetcher.py` | Used for technical analysis and P&L estimate. |
| RSI | `UI/analysis_engine.py` | Calculated from close-price changes. |
| Technical score | `UI/analysis_engine.py` | Based on price return, MA50, MA200, and RSI. |
| Fundamentals score | `UI/fundamentals_fetcher.py` | Based on revenue growth, EPS growth, margins, cash flow, and leverage. |
| Valuation score | `UI/analysis_engine.py` | Based on Yahoo valuation ratios and free-cash-flow yield. |
| Portfolio risk | `UI/analysis_engine.py` | Based on paper holdings, current market value, sector exposure, and selected risk profile. |
| Watchlist signal | `UI/app.py` | Recalculated from the current analysis instead of trusting stored sample labels. |
| What-if scenario impact | `UI/ai_feature_helpers.py` | Python calculates dollar impact before the LLM explains it. |

## LLM / AI Usage

The LLM explains app data. It does not fetch market data and should not invent new numbers.

| Feature | What The LLM Does |
|---|---|
| AI Chat | Answers questions using current dashboard context. |
| Ask AI Why | Explains why the current recommendation was produced. |
| AI Fundamentals Explanation | Explains the loaded Yahoo fundamentals for the selected ticker. |
| AI Portfolio Narrative | Summarizes portfolio value, cash, P&L, concentration, and next research step. |
| AI Trade Journal | Writes a note explaining a simulated paper trade. |
| AI What-If Explanation | Explains a Python-calculated what-if result. |
| AI Fallback Plan | Suggests a research fallback using only provided peer/watchlist candidates. |
| Compare Peers | Explains peer comparison using app-provided peer analysis data. |
| News Sentiment Explainer | Explains the sample news sentiment data shown in the app. |

Relevant files:

- `UI/llm_chat.py`
- `UI/app.py`
- `UI/ai_feature_helpers.py`

## LLM Guardrails

The LLM prompts include grounding rules:

- Use only the JSON context supplied by the app.
- Do not invent prices, ratios, headlines, forecasts, analyst ratings, or holdings.
- If data is missing or unavailable, say it is missing.
- Keep numbers exactly as supplied.
- Separate observed data from interpretation.
- Frame outputs as research support or paper-trading simulation, not personal financial advice.

## Sample Data Still Used

These areas are intentionally still sample/demo data and are labeled in the UI as `sample data`.

| App Area | Where It Comes From | Notes |
|---|---|---|
| News sentiment score | `UI/analysis_engine.py` | Simulated score and signal. |
| News themes | `UI/analysis_engine.py` | Simulated themes like earnings outlook, analyst coverage, and demand trends. |
| Positive/risk headlines | `UI/analysis_engine.py` | Simulated headlines, not live news. |
| Event risk | `UI/analysis_engine.py` | Simulated event score and notes. |
| Backtesting | `UI/analysis_engine.py` | Simulated returns, win rate, drawdown, and trade rows. |
| Seeded paper trades | `UI/paper_portfolio.json` | Simulated historical buys for demo portfolio setup. |
| Seed generator | `UI/portfolio_store.py` | Creates simulated historical buy records if the portfolio file does not exist. |

## Fallback Behavior

When Yahoo Finance data is unavailable:

- Price history falls back to a demo price series so the app can continue running.
- Fundamentals show `N/A` instead of fake values.
- Valuation shows a limited valuation note if fundamentals are unavailable.
- Company profile may use local profile hints for known tickers.
- Portfolio current prices may fall back to the latest paper-trade price.

## Recommended Hackathon Explanation

Use this explanation during the demo:

> Yahoo Finance provides market, company, and fundamentals data. Python calculates technical indicators, valuation, portfolio risk, watchlist signals, and what-if impacts. The LLM explains those results using strict grounding rules. News sentiment, event risk, backtesting, and seeded paper trades are sample data and are clearly labeled in the UI.
