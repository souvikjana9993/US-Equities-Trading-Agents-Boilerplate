from fastapi import FastAPI, HTTPException
from agents.trading_agent import (
    create_technical_agent, 
    create_fundamental_agent, 
    create_news_agent,
    create_orchestrator_agent
)
from models.schemas import (
    TechnicalAnalysisResponse, 
    FundamentalAnalysisResponse, 
    DashboardResponse,
    ChatRequest,
    ChatResponse
)
import uvicorn
import json
import re
import asyncio

app = FastAPI(title="US Stocks Trading Agents API")

# Initialize agents
tech_agent = create_technical_agent()
fund_agent = create_fundamental_agent()
news_agent = create_news_agent()
master_agent = create_orchestrator_agent()

def extract_json(text: str) -> dict:
    """Extracts JSON from agent response string."""
    try:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(text.strip())
    except Exception:
        raise ValueError(f"Could not parse JSON from response: {text[:100]}...")

@app.get("/dashboard/{ticker}", response_model=DashboardResponse)
async def get_dashboard(ticker: str):
    """
    Main Orchestration Endpoint.
    Runs all specialized agents in parallel and aggregates the result.
    """
    try:
        # Step 1: Run specialized agents in parallel
        # Note: strands agents call is blocking, so we use to_thread
        tech_task = asyncio.to_thread(tech_agent, f"Analyze {ticker}")
        fund_task = asyncio.to_thread(fund_agent, f"Analyze {ticker}")
        news_task = asyncio.to_thread(news_agent, f"Analyze {ticker}")
        
        tech_res, fund_res, news_res = await asyncio.gather(tech_task, fund_task, news_task)
        
        # Step 2: Pass all results to the Master Orchestrator
        final_prompt = (
            f"Ticker: {ticker}\n"
            f"Technical: {tech_res}\n"
            f"Fundamental: {fund_res}\n"
            f"News: {news_res}\n"
        )
        
        master_res = master_agent(final_prompt)
        dashboard_data = extract_json(str(master_res))
        
        return DashboardResponse(**dashboard_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat Preview interface.
    Routes queries to the appropriate agent.
    """
    try:
        target_agent = master_agent
        if request.agent_type == "technical":
            target_agent = tech_agent
        elif request.agent_type == "fundamental":
            target_agent = fund_agent
            
        response = target_agent(f"Stock: {request.ticker}. Question: {request.message}")
        return ChatResponse(response=str(response))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/technical/{ticker}", response_model=TechnicalAnalysisResponse)
async def analyze_technical(ticker: str):
    try:
        response_text = tech_agent(f"Analyze the technicals for {ticker}")
        analysis_data = extract_json(str(response_text))
        return TechnicalAnalysisResponse(**analysis_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fundamental/{ticker}", response_model=FundamentalAnalysisResponse)
async def analyze_fundamental(ticker: str):
    try:
        response_text = fund_agent(f"Analyze the fundamentals for {ticker}")
        analysis_data = extract_json(str(response_text))
        return FundamentalAnalysisResponse(**analysis_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news/{ticker}")
async def analyze_news(ticker: str):
    try:
        response_text = news_agent(f"Summarize the recent news sentiment for {ticker}")
        return {"ticker": ticker, "analysis": str(response_text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
