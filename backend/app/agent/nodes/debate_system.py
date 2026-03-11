"""
Debate System Node — Internal critique of hypotheses from multiple angles.
"""
import time
from ..state import ARIAState
from ..context import get_queue, check_pause_and_abort

async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)

import json
from langchain_core.messages import HumanMessage, SystemMessage
from ...llm import get_llm
from ...logger import get_logger

logger = get_logger(__name__)

async def debate_system_node(state: ARIAState) -> dict:
    """Simulate a multi-agent debate to challenge hypotheses."""
    await check_pause_and_abort(state.get("run_id"))
    hypotheses = state.get("hypotheses", [])
    evidence = state.get("extracted_evidence", [])
    start_time = time.time()

    await _emit({"type": "node_start", "node": "debate_system", "label": "Simulating multi-agent debate..."})

    if not hypotheses:
        return {"debate_log": [], "node_timings": {**state.get("node_timings", {}), "debate_system": 0}}

    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Multi-Agent Debate System. Your job is to simulate a "
        "focused debate between internal 'agents' to challenge the proposed hypotheses.\n\n"

        "## Task\n"
        "Take the provided hypotheses and evidence. For each hypothesis, generate: \n"
        "1. **Pro-argument**: Why this conclusion is likely correct.\n"
        "2. **Counter-argument**: Potential flaws, missing data, or alternative interpretations.\n"
        "3. **Synthesis**: A refined view based on the debate.\n\n"

        "## Constraints\n"
        "- Be critical but constructive.\n"
        "- Cite specific evidence where possible.\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON object containing a list `debate_log` (strings summarizing the debate for each hypothesis)."
    ))

    human = HumanMessage(content=(
        f"Goal: {state['goal']}\n"
        f"Hypotheses: {json.dumps(hypotheses, indent=2)}\n"
        f"Evidence: {json.dumps(evidence[:15], indent=2)}"
    ))

    response = await llm.ainvoke([system, human])
    
    try:
        data = json.loads(response.content)
        debate_log = data.get("debate_log", [])
        if isinstance(data, list): debate_log = data
    except Exception as e:
        logger.error(f"Failed to parse Debate System JSON: {e}")
        debate_log = []
    
    duration_ms = int((time.time() - start_time) * 1000)
    await _emit({"type": "node_done", "node": "debate_system", "duration_ms": duration_ms})

    return {
        "debate_log": debate_log,
        "node_timings": {**state.get("node_timings", {}), "debate_system": duration_ms}
    }
