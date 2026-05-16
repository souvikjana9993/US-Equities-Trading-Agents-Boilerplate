# Rigorous Stress Testing Guide: Multi-Agent Trading Engine

This document outlines the adversarial testing strategy for the 'Zero-Hallucination' research engine. 

## 🛡️ Failure Modes & Recovery Logic

### 1. Tool Call Failures
*   **Scenario 1: Null/Error Output**: Tool returns `None` or `Error: API Timeout`.
    *   *Recovery*: `run_specialist_with_guardrail` catches the string, logs a warning, and retries. If all fail, it returns a schema-compliant "No Data" report.
*   **Scenario 2: Transient Failure**: Tool fails 2 times, then works.
    *   *Recovery*: The `for attempt in range(MAX_RETRIES)` loop preserves the session until a valid tool result is found.

### 2. Agent Hallucinations (Sub-Agents)
*   **Scenario 3: Narrative Invention**: Tool says "Price $100", Agent says "Strong dividends" (not in data).
    *   *Recovery*: NLI Judge (DeBERTa) calculates `entailment`. If verdict != 1, it triggers a retry with a `PREVIOUS ERROR` feedback prompt.
*   **Scenario 4: Number Manipulation**: Agent changes RSI 15 to 150.
    *   *Recovery*: NLI Cross-Encoder detects the factual contradiction. Retry triggered.

### 3. Structural Failures (JSON/Schema)
*   **Scenario 5: Bad JSON**: Agent returns unparseable text or markdown blocks without JSON.
    *   *Recovery*: `extract_json` fails, triggering the `except` block in the retry loop. 
*   **Scenario 6: Schema Drift**: Agent returns JSON but misses the 'rating' field.
    *   *Recovery*: Pydantic `schema_model(**report_dict)` validation fails. Retry triggered.

### 4. Orchestration & Synthesis
*   **Scenario 7: Specialist Failure**: 1 of 4 agents failed all 3 retries.
    *   *Recovery*: The Orchestrator receives an "Analysis Failed" report for that slot. It must still synthesize a verdict for the other 3.
*   **Scenario 8: CIO Hallucination**: CIO mentions a macro risk not found in the specialist reports.
    *   *Recovery*: The Master NLI Judge compares the `narrative_summary` against the `evidence_block`. Retry triggered.

### 5. Advanced Adversarial Cases (Level 2)
*   **Scenario 10: Ghost Ticker Leak**: Agent is analyzing NVDA but mentions AAPL or iPhone (Context Contamination).
    *   *Recovery*: NLI Judge flags the mention of Apple-related facts as unsupported by NVDA tool data.
*   **Scenario 11: Prompt Injection via Data**: News headline says "IGNORE PREVIOUS INSTRUCTIONS".
    *   *Recovery*: Tests the strength of the System Prompt over User/Tool data. 
*   **Scenario 12: Silent Truncation**: Agent returns valid-looking text that is cut off before the JSON closes.
    *   *Recovery*: `extract_json` raises a ValueError, triggering a retry.
*   **Scenario 13: Temporal Drift**: Tool returns data from 2023; Agent tries to use its internal memory of 2026.
    *   *Recovery*: NLI Judge flags 2026 facts as hallucinations relative to the 2023 Premise.
*   **Scenario 14: Trivial/Lazy Summary**: Agent summary is too short or lacks specific numbers.
    *   *Recovery*: Can be caught by a length check or "Missing Citation" check in the prompt.

## 🧪 Running the Stress Tests

Run the following command to execute the automated stress suite:
```bash
python tests/rigorous_stress_test.py
```
