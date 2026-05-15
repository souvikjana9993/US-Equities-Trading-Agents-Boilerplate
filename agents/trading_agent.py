from strands import Agent
from strands.models.litellm import LiteLLMModel
from tools.technical_tool import get_comprehensive_technical_analysis
from tools.fundamental_tool import get_comprehensive_fundamentals
from tools.news_tool import get_recent_news_sentiment
from tools.mcp_manager import get_financial_mcp_client
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
import json

def create_agent_with_config(cfg, system_prompt, tools=None):
    model = LiteLLMModel(
        model_id=cfg["model"],
        params={"temperature": cfg["temperature"]}
    )
    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools or []
    )

def create_technical_agent(ticker: str, period: str):
    cfg = config.AGENT_CONFIG["technical"]
    schema = TechnicalReport.model_json_schema()
    prompt = TECHNICAL_ANALYSIS_PROMPT.format(
        ticker=ticker, 
        period=period, 
        schema=json.dumps(schema)
    )
    return create_agent_with_config(cfg, prompt, tools=[get_comprehensive_technical_analysis])

def create_fundamental_agent(ticker: str, period: str):
    cfg = config.AGENT_CONFIG["fundamental"]
    schema = FundamentalReport.model_json_schema()
    prompt = FUNDAMENTAL_ANALYSIS_PROMPT.format(
        ticker=ticker, 
        period=period, 
        schema=json.dumps(schema)
    )
    return create_agent_with_config(cfg, prompt, tools=[get_comprehensive_fundamentals])

def create_news_agent(ticker: str, period: str):
    cfg = config.AGENT_CONFIG["news"]
    schema = NewsReport.model_json_schema()
    prompt = NEWS_SENTIMENT_PROMPT.format(
        ticker=ticker, 
        period=period, 
        schema=json.dumps(schema)
    )
    return create_agent_with_config(cfg, prompt, tools=[get_recent_news_sentiment])

def create_valuation_agent(ticker: str, period: str):
    cfg = config.AGENT_CONFIG["fundamental"]
    schema = ValuationReport.model_json_schema()
    prompt = VALUATION_PROMPT.format(
        ticker=ticker, 
        period=period, 
        schema=json.dumps(schema)
    )
    return create_agent_with_config(cfg, prompt, tools=[get_comprehensive_fundamentals])

def create_orchestrator_agent(ticker: str, period: str, research_reports: str):
    cfg = config.AGENT_CONFIG["orchestrator"]
    schema = DashboardResponse.model_json_schema()
    prompt = MASTER_ORCHESTRATOR_PROMPT.format(
        ticker=ticker, 
        period=period, 
        research_reports=research_reports,
        schema=json.dumps(schema)
    )
    financial_mcp = get_financial_mcp_client()
    tools = [financial_mcp] if (config.USE_MCP and financial_mcp) else []
    return create_agent_with_config(cfg, prompt, tools=tools)

def create_chat_agent(ticker: str, research_context: str):
    cfg = config.AGENT_CONFIG["orchestrator"]
    prompt = CHAT_CONTEXT_PROMPT.format(ticker=ticker, research_context=research_context)
    return create_agent_with_config(cfg, prompt)
