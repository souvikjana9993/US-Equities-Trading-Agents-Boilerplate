# Stock Portfolio Streamlit UI

This folder contains a standalone Streamlit dashboard based on `Documents/stock_portfolio_streamlit_ui_concept.md`.

## Run locally

From the repository root:

```bash
uv sync
.venv/bin/streamlit run UI/app.py --server.port 8511
```

Then open:

```text
http://localhost:8511
```

## Local AI config

The app reads LiteLLM/OpenAI-compatible gateway settings from either the repository root `.env` file or `UI/.env`. These files are ignored by git.

Required values:

```text
LITELLM_BASE_URL="https://your-gateway.example.com/v1"
LITELLM_API_KEY="your-api-key"
LITELLM_MODEL="gpt-5-nano"
```

Use `UI/.env.example` as the masked template. Copy it to `UI/.env` locally and replace the masked API key with the real key.

The sidebar field accepts either a ticker or company name. Inputs like `PEPSI` and `PEPSICO` are resolved through Yahoo Finance search before analysis runs.

## What works now

- Sidebar stock selection, time period, risk profile, and trade mode.
- Sidebar separates current simulated holdings under My Portfolio from future ideas under Future Watchlist.
- Recommendation hero card with Buy/Hold/Sell, confidence, reasoning, and suggested action.
- KPI cards for portfolio value, P&L, cash, risk, and AI confidence.
- Tabs for Overview, Technical Analysis, Fundamentals, News Sentiment, Valuation, Portfolio Risk, Backtesting, and AI Chat.
- Data-derived stock analysis, technical indicators, score breakdowns, portfolio risk warnings, and paper trade simulation.
- Company names are resolved to tickers with Yahoo Finance search through `yfinance`.
- Price charts and technical indicators use Yahoo Finance daily close/volume data through `yfinance`, with fallback demo prices when Yahoo data is unavailable.
- Company profile, sector, and industry are pulled from Yahoo Finance through `yfinance` when available.
- Fundamentals tab pulls expanded company metrics from Yahoo Finance through `yfinance`; unavailable fields are shown as `N/A`.
- Valuation uses Yahoo Finance ratios from the Fundamentals tab such as PE, forward PE, PEG, price/sales, price/book, EV/EBITDA, and free-cash-flow yield.
- Portfolio risk calculates current sector and position exposure from the paper portfolio, current Yahoo prices, and Yahoo sector data when available.
- Fundamentals tab has standard LLM question buttons plus a custom question field. The LLM explains the selected ticker's loaded fundamentals without calculating or inventing new data.
- AI Chat sends context to the LiteLLM/OpenAI-compatible gateway configured in `.env`.
- AI Chat has a stock-specific mode for the selected ticker and a general assistant mode for app usage, watchlist, portfolio simulation, and investing concepts.
- AI Portfolio Narrative summarizes portfolio health, concentration, and one practical next step.
- AI Trade Journal adds an AI rationale note to new paper trades.
- AI What-If Scenario estimates portfolio impact from ticker/portfolio percentage moves and paper-trade reductions such as `sell 50% of AAPL`.
- AI What-If Scenario can also generate a fallback plan and alternative stock to research from supplied peers/watchlist candidates.
- AI Comparative Analysis compares the selected stock against peer candidates.
- AI News Sentiment Explainer summarizes sentiment drivers in plain English.
- Any remaining simulated areas are visibly marked with a `sample data` label in the app.

## LLM prompt pattern

All AI features follow the same grounding rule: Python and data APIs calculate or fetch values, while the LLM explains the supplied context. Prompts tell the model to:

- Use only the JSON context passed by the app.
- Keep numbers exactly as supplied.
- Say when data is missing, fallback, simulated, or demo-only.
- Avoid inventing live prices, news, forecasts, analyst ratings, ratios, or portfolio holdings.
- Frame outputs as research support and paper-trading simulation, not personal financial advice.

## Production extension notes

The app now uses Yahoo Finance for price history, company profile, fundamentals, valuation inputs, and portfolio-risk inputs where possible. The remaining intentionally demo-oriented areas are news sentiment, event risk, backtesting, and the seeded paper portfolio. For a production version, replace those remaining functions in `analysis_engine.py` with:

- Market data from a provider such as Polygon, Alpha Vantage, IEX Cloud, or Yahoo Finance.
- Real fundamentals from financial statements or a market-data API.
- News sentiment from a news API plus an LLM summarizer.
- Portfolio data from the user's brokerage or uploaded holdings.
- A LangGraph workflow only if the team wants true multi-agent orchestration.

Keep numerical calculations in Python. Use an LLM for explanation, summarization, and recommendation synthesis only.
