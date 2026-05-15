import os
from dotenv import load_dotenv

load_dotenv()

# AI Model Configuration
AI_MODEL = os.getenv("AI_MODEL", "gemini/gemini-flash-latest")

# Agent-Specific Settings
AGENT_CONFIG = {
    "technical": {
        "temperature": 0.0,  # Precision is key
        "model": AI_MODEL
    },
    "fundamental": {
        "temperature": 0.1,  # Mostly data-driven
        "model": AI_MODEL
    },
    "news": {
        "temperature": 0.4,  # Needs to interpret sentiment/nuance
        "model": AI_MODEL
    },
    "orchestrator": {
        "temperature": 0.3,  # Synthesizing complex reports
        "model": AI_MODEL
    }
}

# Trading Configuration
DEFAULT_TICKER = "AAPL"
WATCHLIST = ["AAPL", "MSFT", "TSLA", "NVDA"]

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# MCP Configuration
USE_MCP = True
