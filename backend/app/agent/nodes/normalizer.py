"""
Normalization Layer Node — Standardizes extracted facts (units, formats).
"""
import time
from ..state import ARIAState
from ..context import get_queue, check_pause_and_abort

import json
from langchain_core.messages import HumanMessage, SystemMessage
from ...llm import get_llm
from ...logger import get_logger

logger = get_logger(__name__)

async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)

async def normalizer_node(state: ARIAState) -> dict:
    """Standardize units, terminology, and formats in extracted evidence."""
    await check_pause_and_abort(state.get("run_id"))
    evidence = state.get("extracted_evidence", [])
    start_time = time.time()

    await _emit({"type": "node_start", "node": "normalizer", "label": "Normalizing knowledge facts..."})

    if not evidence:
        return {"node_timings": {**state.get("node_timings", {}), "normalizer": 0}}

    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Knowledge Normalization Layer. Your job is to "
        "standardize units, terminology, and formats across extracted research facts.\n\n"

        "## Task\n"
        "Analyze the provided facts and normalize them. Ensure consistency in: \n"
        "- Units (e.g., metric vs imperial)\n"
        "- Dates (e.g., YYYY-MM-DD)\n"
        "- Technical terminology\n"
        "- Currency formats\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY the updated JSON list of `extracted_evidence`."
    ))

    human = HumanMessage(content=f"Facts to Normalize:\n\n{json.dumps(evidence, indent=2)}")

    response = await llm.ainvoke([system, human])
    
    try:
        normalized_evidence = json.loads(response.content)
    except Exception as e:
        logger.error(f"Failed to parse Normalizer JSON: {e}")
        normalized_evidence = evidence
    
    duration_ms = int((time.time() - start_time) * 1000)
    await _emit({"type": "node_done", "node": "normalizer", "duration_ms": duration_ms})

    return {
        "extracted_evidence": normalized_evidence,
        "node_timings": {**state.get("node_timings", {}), "normalizer": duration_ms}
    }
