"""
Strategy Generator Node — Defines specific search strategies and criteria.
"""
import time
from ..state import ARIAState
from ..context import get_queue, check_pause_and_abort

from langchain_core.messages import HumanMessage, SystemMessage
from ...llm import get_llm
from ...logger import get_logger

logger = get_logger(__name__)

async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)

async def strategy_generator_node(state: ARIAState) -> dict:
    """Choose research methodology for the given goal."""
    await check_pause_and_abort(state.get("run_id"))
    goal = state["goal"]
    goal_analysis = state.get("goal_analysis", {})
    start_time = time.time()

    await _emit({"type": "node_start", "node": "strategy_generator", "label": "Defining research strategy..."})

    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Research Strategy Generator. Your job is to define the "
        "methodology and search criteria for the research goal.\n\n"

        "## Task\n"
        "Select the most effective research methodology (e.g., trend analysis, "
        "comparative study, literature review, technical audit, historical timeline) "
        "and define specific success criteria for the discovery phase.\n\n"

        "## Constraints\n"
        "- Choose ONE primary methodology.\n"
        "- Define 3-4 specific search themes.\n"
        "- Suggest quality filters for URLs (e.g., preference for .gov, .edu, specific industry blogs).\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON object:\n"
        '{\n'
        '  "primary_methodology": "method name",\n'
        '  "search_themes": ["theme 1", "theme 2"],\n'
        '  "discovery_criteria": "specific quality signals to look for in sources",\n'
        '  "strategic_rationale": "why this method was chosen"\n'
        '}'
    ))

    human = HumanMessage(content=(
        f"Goal: {goal}\n"
        f"Intent: {goal_analysis.get('intent', 'research')}\n"
        f"Scope: {goal_analysis.get('scope', 'comprehensive')}"
    ))

    response = await llm.ainvoke([system, human])
    
    # Simple extraction for now
    strategy_text = response.content
    
    duration_ms = int((time.time() - start_time) * 1000)
    await _emit({"type": "node_done", "node": "strategy_generator", "duration_ms": duration_ms})

    return {
        "research_strategy": strategy_text,
        "node_timings": {**state.get("node_timings", {}), "strategy_generator": duration_ms}
    }
