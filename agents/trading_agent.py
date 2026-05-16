import os
import json
import time
import google.generativeai as genai
from strands import Agent
from models.schemas import (
    TechnicalReport, 
    FundamentalReport, 
    NewsReport, 
    ValuationReport, 
    DashboardResponse
)
from prompts.trading_prompts import (
    TECHNICAL_ANALYSIS_PROMPT, 
    FUNDAMENTAL_ANALYSIS_PROMPT, 
    NEWS_SENTIMENT_PROMPT,
    VALUATION_PROMPT,
    MASTER_ORCHESTRATOR_PROMPT,
    CHAT_CONTEXT_PROMPT
)
import config

# --- GOOGLE SDK BRIDGE (HARDENED) ---
class GoogleSDKModel:
    def __init__(self, model_id, temperature=0.0):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        # Remove prefixes like 'gemini/' or 'models/'
        self.model_id = model_id.replace("gemini/", "").replace("models/", "")
        self.temperature = temperature
        self.model = genai.GenerativeModel(self.model_id)

    def __call__(self, prompt):
        # Retry loop for 500/Transient errors
        for attempt in range(3):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(temperature=self.temperature)
                )
                return response.text
            except Exception as e:
                if attempt == 2: raise e
                print(f"Retrying Google SDK call ({attempt+1}/3) due to: {e}")
                time.sleep(2 * (attempt + 1))
        return ""

def create_agent_with_config(cfg, system_prompt, tools=None):
    # Using our Bulletproof SDK Bridge with internal retries
    model = GoogleSDKModel(
        model_id=cfg["model"],
        temperature=cfg["temperature"]
    )
    
    # We return a callable that Strands can treat as an agent
    def agent_fn(message):
        full_prompt = f"{system_prompt}\n\nUSER MESSAGE: {message}"
        return model(full_prompt)
        
    return agent_fn

# --- AGENT FACTORIES ---

def create_technical_agent(ticker: str, period: str):
    cfg = config.AGENT_CONFIG["technical"]
    schema = TechnicalReport.model_json_schema()
    prompt = TECHNICAL_ANALYSIS_PROMPT.format(
        ticker=ticker, 
        period=period, 
        schema=json.dumps(schema)
    )
    return create_agent_with_config(cfg, prompt)

def create_fundamental_agent(ticker: str, period: str):
    cfg = config.AGENT_CONFIG["fundamental"]
    schema = FundamentalReport.model_json_schema()
    prompt = FUNDAMENTAL_ANALYSIS_PROMPT.format(
        ticker=ticker, 
        period=period, 
        schema=json.dumps(schema)
    )
    return create_agent_with_config(cfg, prompt)

def create_news_agent(ticker: str, period: str):
    cfg = config.AGENT_CONFIG["news"]
    schema = NewsReport.model_json_schema()
    prompt = NEWS_SENTIMENT_PROMPT.format(
        ticker=ticker, 
        period=period, 
        schema=json.dumps(schema)
    )
    return create_agent_with_config(cfg, prompt)

def create_valuation_agent(ticker: str, period: str):
    cfg = config.AGENT_CONFIG["fundamental"]
    schema = ValuationReport.model_json_schema()
    prompt = VALUATION_PROMPT.format(
        ticker=ticker, 
        period=period, 
        schema=json.dumps(schema)
    )
    return create_agent_with_config(cfg, prompt)

def create_orchestrator_agent(ticker: str, period: str, research_reports: str):
    cfg = config.AGENT_CONFIG["orchestrator"]
    schema = DashboardResponse.model_json_schema()
    prompt = MASTER_ORCHESTRATOR_PROMPT.format(
        ticker=ticker, 
        period=period, 
        research_reports=research_reports,
        schema=json.dumps(schema)
    )
    return create_agent_with_config(cfg, prompt)

def create_chat_agent(ticker: str, research_context: str):
    cfg = config.AGENT_CONFIG["orchestrator"]
    prompt = CHAT_CONTEXT_PROMPT.format(ticker=ticker, research_context=research_context)
    return create_agent_with_config(cfg, prompt)
