import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.trading_agent import create_orchestrator_agent

def test_cio_logic():
    ticker = "NVDA"
    period = "1y"
    
    # Mock specialist reports (including the No News case)
    mock_reports = {
        "Technical": '{"rating": 0.8, "summary": "Strong trend but near resistance.", "label": "Bullish"}',
        "Fundamental": '{"rating": 0.95, "summary": "Exceptional earnings growth.", "label": "Strong"}',
        "News": '{"rating": 0.5, "summary": "No recent news found for NVDA.", "label": "No Data"}',
        "Valuation": '{"rating": 0.6, "summary": "Fairly valued given growth.", "label": "Fair"}'
    }
    
    print("Testing CIO Synthesis with Gemini 2.0 Flash...")
    orchestrator = create_orchestrator_agent(ticker, period, json.dumps(mock_reports))
    
    try:
        final_report = orchestrator("Synthesize these reports.")
        print("\n--- CIO RESPONSE ---")
        print(final_report)
    except Exception as e:
        print(f"Error during synthesis: {e}")

if __name__ == "__main__":
    test_cio_logic()
