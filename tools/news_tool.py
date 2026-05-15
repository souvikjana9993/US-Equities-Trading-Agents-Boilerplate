from strands import tool
import yfinance as yf
import logging

logger = logging.getLogger("NewsTool")

@tool
def get_recent_news_sentiment(ticker: str) -> str:
    """
    Fetches the latest news headlines for a US stock ticker to gauge market sentiment.
    """
    logger.info(f"Fetching news for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news:
            return f"No recent news found for {ticker}."
            
        # Extract headlines and publishers
        headlines = []
        for item in news[:10]: # Get top 10 news items
            title = item.get('title')
            publisher = item.get('publisher')
            headlines.append(f"- {title} ({publisher})")
            
        return "\n".join(headlines)
    except Exception as e:
        logger.error(f"Error in news fetching: {e}")
        return f"Error: {str(e)}"
