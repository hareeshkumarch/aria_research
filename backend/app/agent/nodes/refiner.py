"""
Refiner Node — Takes critic feedback and optionally does additional research
before re-synthesizing. This creates the iterative improvement loop.
"""
import json
import re
import time
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import ARIAState
from ..context import get_queue, check_pause_and_abort
from ..tools.web_search import web_search
from ...llm import get_llm
from ...logger import get_logger
from ...config import settings

logger = get_logger(__name__)


async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)


async def refiner_node(state: ARIAState) -> dict:
    """
    Refine the output based on critic feedback.
    
    Loop: 1) Analyze what's missing → 2) Do targeted research → 3) Re-emit for synthesis
    """
    await check_pause_and_abort(state.get("run_id"))
    goal = state["goal"]
    critic_feedback = state.get("critic_feedback", "")
    draft = state.get("draft_output", "")
    retry_count = state.get("retry_count", 0)
    tool_results = list(state.get("tool_results", []))
    start_time = time.time()

    await _emit({
        "type": "node_start",
        "node": "refiner",
        "label": f"Refining output (iteration {retry_count})...",
    })

    # Step 1: Ask LLM what additional research is needed
    # Use a faster model for refinement advisory queries to reduce latency (fast mode),
    # while allowing deep mode to keep using the selected provider/model.
    use_fast_refine = state.get("mode", "fast") == "fast"
    llm = get_llm(
        streaming=False,
        provider=(settings.refine_provider if use_fast_refine else state.get("provider")),
        model=(settings.refine_model if use_fast_refine else state.get("model")),
    )

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Research Improvement Advisor. Your job is to identify "
        "specific gaps in a research report and suggest targeted search queries.\n\n"

        "## Task\n"
        "Given critique feedback on a research report, identify the specific gaps "
        "and suggest 1-2 targeted search queries that would fill those gaps.\n\n"

        "## Constraints\n"
        "- Queries must be SPECIFIC — target the exact weakness mentioned in the critique\n"
        "- Include year qualifiers (2024, 2025) for freshness\n"
        "- Use different search angles from the original research\n"
        "- Focus on depth-boosting queries (detailed analysis, case studies, data)\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON array of search queries:\n"
        '["very specific query targeting weakness 1", "specific query for gap 2"]\n\n'

        "## Quality Criteria\n"
        "- Each query must directly address a weakness from the critique\n"
        "- Queries should yield new, complementary information"
    ))
    human = HumanMessage(content=(
        f"Goal: {goal}\n\n"
        f"Critique feedback: {critic_feedback}\n\n"
        f"Current report excerpt:\n{draft[:1500]}"
    ))

    response = await llm.ainvoke([system, human])

    # Step 2: Do targeted research on weak areas
    additional_queries = []
    try:
        match = re.search(r'\[.*?\]', response.content, re.DOTALL)
        if match:
            additional_queries = json.loads(match.group())[:2]
    except Exception as e:
        logger.warning(f"Failed to parse targeted research queries from LLM: {e}")
        additional_queries = [f"{goal} detailed analysis"]

    for query in additional_queries:
        await _emit({
            "type": "tool_call",
            "node": "refiner",
            "tool": "web_search",
            "query": query,
        })

        result, duration_ms = await web_search(query, max_results=3)
        tool_results.append(f"## [Refinement Research] {query}\n\n{result}")

        await _emit({
            "type": "tool_result",
            "node": "refiner",
            "query": query,
            "duration_ms": duration_ms,
        })

    total_duration = int((time.time() - start_time) * 1000)

    await _emit({
        "type": "node_done",
        "node": "refiner",
        "duration_ms": total_duration,
    })

    timings = dict(state.get("node_timings", {}))
    timings["refiner"] = total_duration

    return {
        "tool_results": tool_results,
        "node_timings": timings,
    }
