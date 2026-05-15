from strands import Agent
from strands.models.gemini import GeminiModel
from tools.technical_tool import get_comprehensive_technical_analysis
from tools.fundamental_tool import get_comprehensive_fundamentals
from tools.news_tool import get_recent_news_sentiment
from tools.mcp_manager import get_financial_mcp_client
from models.schemas import TechnicalAnalysisResponse, FundamentalAnalysisResponse, DashboardResponse
from prompts.trading_prompts import (
    TECHNICAL_ANALYSIS_PROMPT, 
    FUNDAMENTAL_ANALYSIS_PROMPT, 
    NEWS_SENTIMENT_PROMPT,
    MASTER_ORCHESTRATOR_PROMPT
)
import config
import json
import os

def create_agent_with_config(cfg, system_prompt, tools=None):
    """Helper to create an agent with specific config using native GeminiModel."""
    # Strip 'gemini/' prefix if present for the native model_id
    model_id = cfg["model"].split("/")[-1] if "/" in cfg["model"] else cfg["model"]
    
    model = GeminiModel(
        model_id=model_id,
        params={"temperature": cfg["temperature"]}
    )
    return Agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools or []
    )

def create_technical_agent():
    """Technical Analysis Specialist."""
    schema = TechnicalAnalysisResponse.model_json_schema()
    cfg = config.AGENT_CONFIG["technical"]
    return create_agent_with_config(
        cfg, 
        TECHNICAL_ANALYSIS_PROMPT.format(schema=json.dumps(schema)),
        tools=[get_comprehensive_technical_analysis]
    )

def create_fundamental_agent():
    """Fundamental Analysis Specialist."""
    schema = FundamentalAnalysisResponse.model_json_schema()
    cfg = config.AGENT_CONFIG["fundamental"]
    return create_agent_with_config(
        cfg, 
        FUNDAMENTAL_ANALYSIS_PROMPT.format(schema=json.dumps(schema)),
        tools=[get_comprehensive_fundamentals]
    )

def create_news_agent():
    """News & Sentiment Specialist."""
    cfg = config.AGENT_CONFIG["news"]
    return create_agent_with_config(
        cfg, 
        NEWS_SENTIMENT_PROMPT,
        tools=[get_recent_news_sentiment]
    )

def create_orchestrator_agent():
    """Master Orchestrator / CIO."""
    schema = DashboardResponse.model_json_schema()
    cfg = config.AGENT_CONFIG["orchestrator"]
    financial_mcp = get_financial_mcp_client()
    
    tools = []
    if config.USE_MCP and financial_mcp:
        tools.append(financial_mcp)
        
    return create_agent_with_config(
        cfg,
        MASTER_ORCHESTRATOR_PROMPT.format(
            schema=json.dumps(schema),
            technical_data="{technical_data}",
            fundamental_data="{fundamental_data}",
            news_data="{news_data}"
        ),
        tools=tools
    )
