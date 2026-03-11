"""
Hypothesis Generation Node — Proposes potential answers/conclusions.
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

async def hypothesis_generator_node(state: ARIAState) -> dict:
    """Generate potential answers and hypotheses based on evidence."""
    await check_pause_and_abort(state.get("run_id"))
    evidence = state.get("extracted_evidence", [])
    kg = state.get("knowledge_graph", [])
    start_time = time.time()

    await _emit({"type": "node_start", "node": "hypothesis_generator", "label": "Generating research hypotheses..."})

    if not evidence and not kg:
        return {"hypotheses": [], "node_timings": {**state.get("node_timings", {}), "hypothesis_generator": 0}}

    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Hypothesis Generation Agent. Your job is to create "
        "possible explanations and answers based on the collective research evidence.\n\n"

        "## Task\n"
        "Analyze the extracted evidence and the knowledge graph. Propose 2-3 "
        "distinct hypotheses or potential conclusions that answer the research goal.\n\n"

        "## Constraints\n"
        "- Each hypothesis must be grounded in the provided data.\n"
        "- Ensure the hypotheses cover different facets of the goal.\n"
        "- Formulate them as structured claims.\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON object containing a list of `hypotheses` (strings)."
    ))

    human = HumanMessage(content=(
        f"Goal: {state['goal']}\n"
        f"Evidence: {json.dumps(evidence[:20], indent=2)}\n"
        f"Knowledge Graph: {json.dumps(kg[:10], indent=2)}"
    ))

    response = await llm.ainvoke([system, human])
    
    try:
        data = json.loads(response.content)
        hypotheses = data.get("hypotheses", [])
        if isinstance(data, list):
            hypotheses = data
    except Exception as e:
        logger.error(f"Failed to parse Hypothesis Generator JSON: {e}")
        hypotheses = []
    
    duration_ms = int((time.time() - start_time) * 1000)
    await _emit({"type": "node_done", "node": "hypothesis_generator", "duration_ms": duration_ms})

    return {
        "hypotheses": hypotheses,
        "node_timings": {**state.get("node_timings", {}), "hypothesis_generator": duration_ms}
    }
