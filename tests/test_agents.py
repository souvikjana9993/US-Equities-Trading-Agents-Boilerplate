import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.trading_agent import (
    create_technical_agent, 
    create_fundamental_agent, 
    create_news_agent,
    create_orchestrator_agent
)
import config

async def run_individual_tests(ticker):
    print(f"\n--- Testing Individual Agents for {ticker} ---")
    
    # Technical Agent
    print("Testing Technical Agent...")
    tech_agent = create_technical_agent()
    tech_res = tech_agent(f"Quick check for {ticker}")
    print(f"Technical Result: {str(tech_res)[:200]}...")
    
    # Fundamental Agent
    print("\nTesting Fundamental Agent...")
    fund_agent = create_fundamental_agent()
    fund_res = fund_agent(f"Quick check for {ticker}")
    print(f"Fundamental Result: {str(fund_res)[:200]}...")

async def run_orchestration_test(ticker):
    print(f"\n--- Testing Full Orchestration for {ticker} ---")
    
    tech_agent = create_technical_agent()
    fund_agent = create_fundamental_agent()
    news_agent = create_news_agent()
    master_agent = create_orchestrator_agent()
    
    print("Step 1: Running sub-agents in parallel...")
    tech_task = asyncio.to_thread(tech_agent, f"Analyze {ticker}")
    fund_task = asyncio.to_thread(fund_agent, f"Analyze {ticker}")
    news_task = asyncio.to_thread(news_agent, f"Analyze {ticker}")
    
    tech_res, fund_res, news_res = await asyncio.gather(tech_task, fund_task, news_task)
    
    print("Step 2: Aggregating in Master Agent...")
    final_prompt = (
        f"Ticker: {ticker}\n"
        f"Technical: {tech_res}\n"
        f"Fundamental: {fund_res}\n"
        f"News: {news_res}\n"
    )
    
    master_res = master_agent(final_prompt)
    print(f"\nFINAL DASHBOARD RESPONSE:\n{master_res}")

if __name__ == "__main__":
    ticker = config.DEFAULT_TICKER
    
    async def main():
        # Run individual tests
        await run_individual_tests(ticker)
        # Run full orchestration
        await run_orchestration_test(ticker)

    asyncio.run(main())
