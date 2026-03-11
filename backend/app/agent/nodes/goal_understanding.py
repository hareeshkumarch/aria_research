"""
Goal Understanding Node — Clarifies intent, extracts entities, determines scope.
Inserted between START and planner to normalize raw user goals.
"""
import json
import re
import time
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import ARIAState, GoalAnalysis
from ..context import get_queue, check_pause_and_abort
from ...llm import get_llm



async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)

async def goal_understanding_node(state: ARIAState) -> dict:
    """Parse the user's goal into structured components."""
    await check_pause_and_abort(state.get("run_id"))
    goal = state["goal"]
    start_time = time.time()

    await _emit({
        "type": "node_start",
        "node": "goal_understanding",
        "label": "Understanding your goal...",
    })

    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Goal Understanding module. Your sole responsibility is to "
        "analyze a user's research goal and produce a structured breakdown.\n\n"

        "## Task\n"
        "Parse the user's natural language goal into structured components that will "
        "guide downstream planning and research.\n\n"

        "## Constraints\n"
        "- Do NOT answer the goal itself — only analyze WHAT is being asked\n"
        "- Be specific about entities and scope — avoid vague descriptions\n"
        "- Identify any ambiguities that could lead to misinterpretation\n"
        "- Keep all values concise (1-2 sentences max per field)\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON object:\n"
        '{\n'
        '  "intent": "the core action the user wants (e.g., compare, research, analyze, explain)",\n'
        '  "key_entities": ["entity1", "entity2"],\n'
        '  "scope": "how broad or narrow the research should be",\n'
        '  "expected_output": "what type of deliverable the user expects (report, comparison, summary, etc.)",\n'
        '  "constraints": ["any limitations or requirements implied by the goal"],\n'
        '  "ambiguities": ["anything unclear that we should note"]\n'
        '}\n\n'

        "## Quality Criteria\n"
        "- intent must be a clear verb phrase\n"
        "- key_entities must list all specific subjects, technologies, or concepts\n"
        "- scope should indicate depth and breadth expectations\n"
        "- expected_output should map to a deliverable format"
    ))
    human = HumanMessage(content=f"Goal: {goal}")

    response = await llm.ainvoke([system, human])

    # Parse the structured analysis
    analysis: GoalAnalysis = {
        "intent": "research",
        "key_entities": [],
        "scope": "comprehensive",
        "expected_output": "research report",
        "constraints": [],
        "ambiguities": [],
    }

    try:
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            analysis = {
                "intent": data.get("intent", "research"),
                "key_entities": data.get("key_entities", []),
                "scope": data.get("scope", "comprehensive"),
                "expected_output": data.get("expected_output", "research report"),
                "constraints": data.get("constraints", []),
                "ambiguities": data.get("ambiguities", []),
            }
    except (json.JSONDecodeError, ValueError):
        pass  # Use defaults

    duration_ms = int((time.time() - start_time) * 1000)

    await _emit({
        "type": "goal_understood",
        "node": "goal_understanding",
        "analysis": analysis,
        "duration_ms": duration_ms,
    })
    await _emit({
        "type": "node_done",
        "node": "goal_understanding",
        "duration_ms": duration_ms,
    })

    timings = dict(state.get("node_timings", {}))
    timings["goal_understanding"] = duration_ms

    return {
        "goal_analysis": analysis,
        "node_timings": timings,
    }
