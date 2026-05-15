from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class TechnicalAnalysisResponse(BaseModel):
    ticker: str
    recommendation: str = Field(..., description="BUY, SELL, or HOLD")
    overall_summary: str
    indicators: Dict[str, Any]
    bullish_signals: List[str]
    bearish_signals: List[str]

class FundamentalAnalysisResponse(BaseModel):
    ticker: str
    recommendation: str = Field(..., description="BUY, SELL, or HOLD")
    overall_summary: str
    thesis: str
    key_metrics: Dict[str, Any]
    valuation_status: str

class AgentScore(BaseModel):
    agent_name: str
    score: float = Field(..., ge=0, le=100)
    label: str = Field(..., description="e.g., Bullish, Strong, Positive")

class DashboardResponse(BaseModel):
    ticker: str
    recommendation: str = Field(..., description="BUY, SELL, HOLD")
    confidence_score: float = Field(..., ge=0, le=100)
    summary: str
    suggested_action: str
    scores: List[AgentScore]
    technical_summary: str
    fundamental_summary: str
    news_summary: str

class ChatRequest(BaseModel):
    ticker: str
    message: str
    agent_type: Optional[str] = "orchestrator"

class ChatResponse(BaseModel):
    response: str
