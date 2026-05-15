import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.trading_agent import (
    create_technical_agent, 
    create_fundamental_agent, 
    create_news_agent,
    create_valuation_agent,
    create_orchestrator_agent
)
from tools.technical_tool import get_comprehensive_technical_analysis
from tools.fundamental_tool import get_comprehensive_fundamentals
from tools.news_tool import get_recent_news_sentiment

def save_output(ticker, name, content):
    """Saves research outputs to the research_outputs folder."""
    path = f"research_outputs/{ticker}"
    os.makedirs(path, exist_ok=True)
    filename = f"{path}/{name}.txt"
    with open(filename, "w") as f:
        f.write(str(content))
    print(f"Saved: {filename}")

def test_full_research_recorder():
    ticker = "NVDA"
    period = "1y"
    
    print(f"--- Recording Full Research Session for {ticker} ---")
    
    # 1. Capture RAW Tool Outputs (The Evidence)
    print("Capturing Raw Tool Evidence...")
    raw_tech = get_comprehensive_technical_analysis(ticker)
    save_output(ticker, "00_raw_technical_data", raw_tech)
    
    raw_fund = get_comprehensive_fundamentals(ticker)
    save_output(ticker, "00_raw_fundamental_data", raw_fund)
    
    raw_news = get_recent_news_sentiment(ticker)
    save_output(ticker, "00_raw_news_data", raw_news)
    
    # 2. Setup Agents
    tech_agent = create_technical_agent(ticker, period)
    fund_agent = create_fundamental_agent(ticker, period)
    news_agent = create_news_agent(ticker, period)
    val_agent = create_valuation_agent(ticker, period)
    
    # 3. Run specialists
    print("Running Research Specialists...")
    tech_res = tech_agent(f"Analyze {ticker}")
    save_output(ticker, "01_technical_agent_report", tech_res)
    
    fund_res = fund_agent(f"Analyze {ticker}")
    save_output(ticker, "02_fundamental_agent_report", fund_res)
    
    news_res = news_agent(f"Analyze {ticker}")
    save_output(ticker, "03_news_agent_report", news_res)
    
    val_res = val_agent(f"Analyze {ticker}")
    save_output(ticker, "04_valuation_expansion_report", val_res)
    
    research_context = {
        "Technical": str(tech_res),
        "Fundamental": str(fund_res),
        "News": str(news_res),
        "Valuation": str(val_res)
    }
    
    # 4. Synthesis
    print("Orchestrating final synthesis...")
    orchestrator = create_orchestrator_agent(ticker, period, json.dumps(research_context))
    final_report = orchestrator(f"Synthesize research for {ticker}")
    save_output(ticker, "05_final_orchestrator_json", final_report)
    
    print(f"\n--- SUCCESS: Raw data and Agent reports for {ticker} are saved in research_outputs/{ticker} ---")

if __name__ == "__main__":
    test_full_research_recorder()
