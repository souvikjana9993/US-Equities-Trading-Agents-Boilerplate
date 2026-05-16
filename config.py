import os
from dotenv import load_dotenv

load_dotenv()

# AI Model Configuration - REVERTING TO STABLE DEFAULT
AI_MODEL = os.getenv("AI_MODEL", "models/gemma-4-26b-a4b-it")

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
