from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

# --- Specialist Report Schemas ---

class SpecialistReport(BaseModel):
    rating: float = Field(..., ge=0.0, le=1.0)
    summary: str
    label: str

class TechnicalReport(SpecialistReport): pass
class FundamentalReport(SpecialistReport): pass
class NewsReport(SpecialistReport): pass
class ValuationReport(SpecialistReport): pass

# --- Orchestrator Verdict Schema ---

class OrchestratorVerdict(BaseModel):
    """The final decision-making output from the CIO."""
    suggested_action: str  # BUY, SELL, HOLD
    confidence_rating: float = Field(..., ge=0.0, le=1.0)
    narrative_summary: str

# --- Final Dashboard & UI Schemas ---

class AgentScore(BaseModel):
    agent_name: str
    rating: float
    summary: str
    label: str

class DashboardResponse(BaseModel):
    """Final merged research session (Validated)."""
    ticker: str
    period: str
    suggested_action: str
    confidence_rating: float
    narrative_summary: str
    
    # These come directly from specialists (The 'Ground Truth')
    scores: List[AgentScore]
    
    # Internal context (used for chat hydration)
    research_context: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    ticker: str
    period: str = "1y"
    message: str

class ChatResponse(BaseModel):
    response: str
