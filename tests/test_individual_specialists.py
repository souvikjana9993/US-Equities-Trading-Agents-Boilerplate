import asyncio
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.trading_agent import (
    create_technical_agent, 
    create_fundamental_agent, 
    create_news_agent,
    create_valuation_agent
)

async def test_all():
    ticker = "NVDA"
    period = "1y"
    
    agents = {
        "Technical": create_technical_agent(ticker, period),
        "Fundamental": create_fundamental_agent(ticker, period),
        "News": create_news_agent(ticker, period),
        "Valuation": create_valuation_agent(ticker, period)
    }
    
    for name, agent in agents.items():
        print(f"\n--- Testing {name} Specialist ---")
        try:
            res = await asyncio.to_thread(agent, f"Analyze {ticker}")
            print(f"SUCCESS: {name} responded.")
            print(res[:200] + "...")
        except Exception as e:
            print(f"FAILED: {name} encountered error: {e}")

if __name__ == "__main__":
    asyncio.run(test_all())
