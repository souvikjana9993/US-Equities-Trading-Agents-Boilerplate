import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.technical_tool import get_comprehensive_technical_analysis
from tools.fundamental_tool import get_comprehensive_fundamentals
import json

def test_tools():
    ticker = "AAPL"
    print(f"--- Testing Technical Tool for {ticker} ---")
    tech_result = get_comprehensive_technical_analysis(ticker)
    print(tech_result)
    
    print(f"\n--- Testing Fundamental Tool for {ticker} ---")
    fund_result = get_comprehensive_fundamentals(ticker)
    print(fund_result)

if __name__ == "__main__":
    test_tools()
