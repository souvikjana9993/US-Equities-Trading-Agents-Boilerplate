import os
from dotenv import load_dotenv

load_dotenv()

# AI Model Configuration - REVERTING TO STABLE DEFAULT
AI_MODEL = os.getenv("AI_MODEL", "gemini/gemma-4-31b-it")

# Agent-Specific Settings
AGENT_CONFIG = {
    "technical": {
        "temperature": 0.0,
        "model": AI_MODEL
    },
    "fundamental": {
        "temperature": 0.1,
        "model": AI_MODEL
    },
    "news": {
        "temperature": 0.4,
        "model": AI_MODEL
    },
    "orchestrator": {
        "temperature": 0.0,
        "model": "gemini/gemini-2.5-flash"
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
