from strands import tool
import yfinance as yf
import logging
import pandas as pd

logger = logging.getLogger("FundamentalTool")

@tool
def get_comprehensive_fundamentals(ticker: str) -> str:
    """
    Fetches comprehensive fundamental data for a given US stock ticker.
    Includes financials, balance sheet, cash flow, and key valuation metrics.
    """
    logger.info(f"Fetching comprehensive fundamentals for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Helper to safely get nested info
        def safe_get(d, key, default="N/A"):
            val = d.get(key, default)
            return val if val is not None else default

        summary = {
            "business_summary": safe_get(info, "longBusinessSummary"),
            "valuation": {
                "market_cap": safe_get(info, "marketCap"),
                "trailing_pe": safe_get(info, "trailingPE"),
                "forward_pe": safe_get(info, "forwardPE"),
                "price_to_book": safe_get(info, "priceToBook"),
                "ev_to_ebitda": safe_get(info, "enterpriseToEbitda"),
            },
            "profitability": {
                "profit_margins": safe_get(info, "profitMargins"),
                "operating_margins": safe_get(info, "operatingMargins"),
                "return_on_equity": safe_get(info, "returnOnEquity"),
                "return_on_assets": safe_get(info, "returnOnAssets"),
            },
            "growth": {
                "revenue_growth": safe_get(info, "revenueGrowth"),
                "earnings_growth": safe_get(info, "earningsGrowth"),
            },
            "financial_health": {
                "total_debt": safe_get(info, "totalDebt"),
                "debt_to_equity": safe_get(info, "debtToEquity"),
                "current_ratio": safe_get(info, "currentRatio"),
                "free_cashflow": safe_get(info, "freeCashflow"),
            }
        }
        
        # Adding a snapshot of recent financials if available
        try:
            financials = stock.quarterly_financials
            if not financials.empty:
                recent_revenue = financials.loc['Total Revenue'].iloc[:4].to_dict()
                summary["recent_quarterly_revenue"] = {str(k.date()): v for k, v in recent_revenue.items()}
        except:
            pass

        return str(summary)
    except Exception as e:
        logger.error(f"Error in comprehensive fundamentals: {e}")
        return f"Error: {str(e)}"
