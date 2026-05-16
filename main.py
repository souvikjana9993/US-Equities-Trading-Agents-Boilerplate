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
from tools.guardrails import global_guardrail
from tools.technical_tool import get_comprehensive_technical_analysis
from tools.fundamental_tool import get_comprehensive_fundamentals
from tools.news_tool import get_recent_news_sentiment

import uvicorn
import json
import re
import asyncio
import logging

app = FastAPI(title="Intelligence Engine: Guarded Synthesis")
MAX_RETRIES = 3

def extract_json(text: str) -> dict:
    try:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(text.strip())
    except Exception:
        raise ValueError(f"Could not parse JSON from response: {text[:100]}...")

async def run_specialist_with_guardrail(name, agent_factory, tool_func, ticker, period, schema_model):
    """
    Runs a specialist agent with manual tool execution, NLI guardrails, and retry logic.
    """
    last_error = ""
    
    for attempt in range(MAX_RETRIES):
        try:
            # 1. Fetch RAW data (The Premise)
            raw_data = await asyncio.to_thread(tool_func, ticker)
            
            # If data is missing, we still try a few times (could be a transient API failure)
            if "Error" in raw_data or "Insufficient data" in raw_data:
                last_error = f"Source tool reported: {raw_data}"
                logging.warning(f"Attempt {attempt+1}: Data missing for {name} on {ticker}. Retrying...")
                await asyncio.sleep(1) # Small backoff
                continue

            # 2. Run Agent
            agent = agent_factory(ticker, period)
            prompt = f"Analyze {ticker} research. DATA: {raw_data}"
            if last_error:
                prompt += f"\n\nNOTE: Previous attempt failed with: {last_error}. Please correct this."
            
            res = await asyncio.to_thread(agent, prompt)
            report_dict = extract_json(str(res))
            validated_report = schema_model(**report_dict)
            
            # 3. NLI Guardrail Check
            if global_guardrail.check_entailment(raw_data, validated_report.summary):
                logging.info(f"Guardrail passed for {name} on attempt {attempt+1}")
                return validated_report
            else:
                last_error = "Hallucination detected. Agent summary included facts NOT present in the raw data."
                logging.warning(f"Guardrail failed for {name} on attempt {attempt+1}")
                
        except Exception as e:
            last_error = str(e)
            logging.error(f"Error in {name} attempt {attempt+1}: {e}")
        
        await asyncio.sleep(1) # Backoff between retries

    # Final Fallback
    logging.error(f"All {MAX_RETRIES} attempts failed for {name}. Returning error state.")
    return schema_model(rating=0.5, summary=f"Research failed for {name} after multiple attempts. Last error: {last_error}", label="Analysis Failed")

@app.get("/dashboard/{ticker}", response_model=DashboardResponse)
async def get_dashboard(ticker: str, period: str = "1y"):
    cached_data = global_research_cache.get(ticker, period)
    if cached_data:
        return DashboardResponse(**cached_data)

    try:
        # 1. Run Specialists with Guardrails & Retries
        tech_data = await run_specialist_with_guardrail("Technical", create_technical_agent, get_comprehensive_technical_analysis, ticker, period, TechnicalReport)
        fund_data = await run_specialist_with_guardrail("Fundamental", create_fundamental_agent, get_comprehensive_fundamentals, ticker, period, FundamentalReport)
        news_data = await run_specialist_with_guardrail("News", create_news_agent, get_recent_news_sentiment, ticker, period, NewsReport)
        
        # 2. Valuation expansion (Guarded by Fundamental summary)
        async def mock_val_tool(t): return fund_data.summary # Premise is the fundamental findings
        val_data = await run_specialist_with_guardrail("Valuation", create_valuation_agent, mock_val_tool, ticker, period, ValuationReport)
        
        specialist_scores = [
            AgentScore(agent_name="Technical", **tech_data.model_dump()),
            AgentScore(agent_name="Fundamental", **fund_data.model_dump()),
            AgentScore(agent_name="News", **news_data.model_dump()),
            AgentScore(agent_name="Valuation", **val_data.model_dump())
        ]
        
        # 3. CIO Synthesis (Guarded by Specialist Reports)
        research_context = {s.agent_name: s.model_dump() for s in specialist_scores}
        evidence_block = "\n".join([f"{s.agent_name}: {s.summary}" for s in specialist_scores])
        
        last_orchestrator_error = ""
        verdict = None
        
        for attempt in range(MAX_RETRIES):
            try:
                orchestrator = create_orchestrator_agent(ticker, period, json.dumps(research_context))
                orc_prompt = f"Final synthesis for {ticker}."
                if last_orchestrator_error:
                    orc_prompt += f"\n\nERROR IN PREVIOUS ATTEMPT: {last_orchestrator_error}. Please stick strictly to the evidence."
                
                master_res = await asyncio.to_thread(orchestrator, orc_prompt)
                verdict_dict = extract_json(str(master_res))
                verdict = OrchestratorVerdict(**verdict_dict)
                
                # NLI Guardrail for CIO
                if global_guardrail.check_entailment(evidence_block, verdict.narrative_summary):
                    logging.info(f"CIO Guardrail passed on attempt {attempt+1}")
                    break
                else:
                    last_orchestrator_error = "Hallucination in synthesis. Narrative contains claims not found in specialist reports."
                    logging.warning(f"CIO Guardrail failed on attempt {attempt+1}")
            except Exception as e:
                last_orchestrator_error = str(e)
                logging.error(f"CIO attempt {attempt+1} failed: {e}")
            
            await asyncio.sleep(1)

        if not verdict:
            raise HTTPException(status_code=500, detail="Orchestrator failed to produce a valid synthesis after retries.")

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
        logging.error(f"Synthesis Chain Failed: {e}")
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
