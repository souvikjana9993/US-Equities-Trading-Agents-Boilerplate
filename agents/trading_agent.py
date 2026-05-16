import os
import json
from strands import Agent
from strands.models.gemini import GeminiModel
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

def create_agent_with_config(cfg, system_prompt, tools=None):
    # Restoring native Strands GeminiModel
    model = GeminiModel(
        model_id=cfg["model"].replace("gemini/", ""),
        client_args={
            "api_key": os.getenv("GOOGLE_API_KEY"),
            "http_options": {"api_version": "v1beta"} # Defaulting back to v1beta with correct model name
        },
        params={"temperature": cfg["temperature"]}
    )
    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools or []
    )

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
