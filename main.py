from fastapi import FastAPI, HTTPException
from agents.trading_agent import (
    create_technical_agent, 
    create_fundamental_agent, 
    create_news_agent,
    create_valuation_agent,
    create_orchestrator_agent,
    create_chat_agent
)
from models.schemas import (
    TechnicalReport, 
    FundamentalReport, 
    NewsReport, 
    ValuationReport, 
    OrchestratorVerdict,
    DashboardResponse,
    AgentScore,
    ChatRequest,
    ChatResponse
)
from tools.cache_manager import global_research_cache
import uvicorn
import json
import re
import asyncio

app = FastAPI(title="Intelligence Engine: Deterministic Synthesis")

def extract_json(text: str) -> dict:
    try:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(text.strip())
    except Exception:
        raise ValueError(f"Could not parse JSON from response: {text[:100]}...")

@app.get("/dashboard/{ticker}", response_model=DashboardResponse)
async def get_dashboard(ticker: str, period: str = "1y"):
    cached_data = global_research_cache.get(ticker, period)
    if cached_data:
        return DashboardResponse(**cached_data)

    try:
        # 1. Run Specialists
        tech_agent = create_technical_agent(ticker, period)
        fund_agent = create_fundamental_agent(ticker, period)
        news_agent = create_news_agent(ticker, period)
        val_agent = create_valuation_agent(ticker, period)
        
        raw_results = await asyncio.gather(
            asyncio.to_thread(tech_agent, f"Analyze {ticker}"),
            asyncio.to_thread(fund_agent, f"Analyze {ticker}"),
            asyncio.to_thread(news_agent, f"Analyze {ticker}"),
            asyncio.to_thread(val_agent, f"Analyze {ticker}")
        )
        
        # 2. Hard Validation of Specialist Reports (The Ground Truth)
        tech_data = TechnicalReport(**extract_json(str(raw_results[0])))
        fund_data = FundamentalReport(**extract_json(str(raw_results[1])))
        news_data = NewsReport(**extract_json(str(raw_results[2])))
        val_data = ValuationReport(**extract_json(str(raw_results[3])))
        
        specialist_scores = [
            AgentScore(agent_name="Technical", **tech_data.model_dump()),
            AgentScore(agent_name="Fundamental", **fund_data.model_dump()),
            AgentScore(agent_name="News", **news_data.model_dump()),
            AgentScore(agent_name="Valuation", **val_data.model_dump())
        ]
        
        # 3. CIO Synthesis (Verdict Only)
        research_context = {s.agent_name: s.model_dump() for s in specialist_scores}
        orchestrator = create_orchestrator_agent(ticker, period, json.dumps(research_context))
        master_res = orchestrator(f"Analyze the research for {ticker}")
        
        verdict = OrchestratorVerdict(**extract_json(str(master_res)))
        
        # 4. Deterministic Merger (Facts from Specialists + Decision from CIO)
        final_output = DashboardResponse(
            ticker=ticker,
            period=period,
            suggested_action=verdict.suggested_action,
            confidence_rating=verdict.confidence_rating,
            narrative_summary=verdict.narrative_summary,
            scores=specialist_scores,
            research_context=research_context
        )
        
        global_research_cache.set(ticker, period, final_output.model_dump())
        return final_output
        
    except Exception as e:
        print(f"Synthesis Chain Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    cached_session = global_research_cache.get(request.ticker, request.period)
    if not cached_session:
        raise HTTPException(status_code=400, detail="Please run 'Analyze' first.")

    try:
        context_str = json.dumps(cached_session["research_context"])
        chat_agent = create_chat_agent(request.ticker, context_str)
        response = chat_agent(request.message)
        return ChatResponse(response=str(response))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
