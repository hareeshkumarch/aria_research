"""
Planner Node — Decomposes a goal into a subtask DAG.
Queries ChromaDB for relevant past memories before planning.
Uses goal_analysis from the Goal Understanding node for better decomposition.
"""
import json
import re
import time
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import ARIAState
from ..context import get_queue, check_pause_and_abort
from ...llm import get_llm
from ...config import settings
from ...memory.chroma import memory_service
from ...repositories.subtasks_repo import save_subtasks
from ...logger import get_logger
from ...cache import get_cached, set_cached, LLM_CACHE_TTL

logger = get_logger(__name__)



def _parse_subtasks(text: str, max_tasks: int = 5) -> list[dict]:
    """Robustly parse subtasks JSON from LLM response."""
    fallback = [{
        "id": "1",
        "title": "Research the goal",
        "query": text[:200] if text else "Research goal",
        "description": "Comprehensive research on the topic",
        "tool_hint": "web_search",
        "status": "pending",
        "result": None,
        "dependencies": [],
        "retry_count": 0,
    }]
    
    match = re.search(r'\[.*?\]', text, re.DOTALL)
    if match:
        try:
            raw = json.loads(match.group())
            tasks = []
            for i, item in enumerate(raw[:max_tasks]):
                deps = item.get("dependencies", [])
                if isinstance(deps, str):
                    deps = [d.strip() for d in deps.split(",") if d.strip()]

                tasks.append({
                    "id": str(i + 1),
                    "title": item.get("title", f"Task {i+1}"),
                    "query": item.get("query", item.get("title", "")),
                    "description": item.get("description", ""),
                    "tool_hint": item.get("tool_hint", "web_search"),
                    "status": "pending",
                    "result": None,
                    "dependencies": [str(d) for d in deps],
                    "retry_count": 0,
                })
            if tasks:
                return tasks
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse planner output as JSON: {e}")

    logger.warning("Planner failed to output valid JSON structure. Using fallback single task.")

    # Fallback: create a single subtask from the goal
    return fallback


async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)

async def planner_node(state: ARIAState) -> dict:
    """Plan subtasks — uses goal analysis + memory, then LLM for decomposition."""
    await check_pause_and_abort(state.get("run_id"))
    goal = state["goal"]
    goal_analysis = state.get("goal_analysis", {})
    mode = state.get("mode", "fast")
    start_time = time.time()

    await _emit({"type": "node_start", "node": "planner", "label": "Planning subtasks..."})

    # 1. Query memory for relevant past research
    memory_context = []
    try:
        memories = await memory_service.retrieve(goal, n_results=5)
        if memories:
            memory_context = [m["text"] for m in memories]
            await _emit({
                "type": "memory_recall",
                "node": "planner",
                "count": len(memories),
                "message": f"Found {len(memories)} relevant memories from past research",
            })
    except Exception as e:
        logger.warning(f"Memory retrieval failed in planner: {e}")

    # 2. Build the planning prompt with goal analysis context
    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    memory_section = ""
    if memory_context:
        memory_section = (
            "\n\n## Relevant Past Research (from ARIA's memory)\n"
            + "\n---\n".join(memory_context[:3])
            + "\n\nUse this context to avoid redundant research and build on past findings."
        )

    # Build goal context from analysis
    goal_context = ""
    if goal_analysis:
        goal_context = (
            "\n\n## Goal Analysis (from upstream module)\n"
            f"- **Intent:** {goal_analysis.get('intent', 'research')}\n"
            f"- **Key Entities:** {', '.join(goal_analysis.get('key_entities', []))}\n"
            f"- **Scope:** {goal_analysis.get('scope', 'comprehensive')}\n"
            f"- **Expected Output:** {goal_analysis.get('expected_output', 'report')}\n"
            f"- **Constraints:** {', '.join(goal_analysis.get('constraints', []))}\n"
            "\nUse this analysis to create more targeted, relevant subtasks."
        )

    available_tools = [
        "web_search — search the web for information",
        "web_fetch — fetch content from a specific URL",
        "recall_memory — search past research memories",
    ]
    if settings.e2b_api_key:
        available_tools.append("code_exec — execute Python code in a sandbox")

    tools_section = "\n".join(f"  - {t}" for t in available_tools)

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Task Planner — an elite autonomous research planner that "
        "decomposes complex goals into actionable subtask DAGs.\n\n"

        "## Task\n"
        "Given a research goal (and its structured analysis), decompose it into "
        f"{'1-3' if mode == 'fast' else '6-8'} "
        "highly specific, diverse subtasks that together provide comprehensive coverage.\n\n"

        "## Constraints\n"
        f"- Create no more than {settings.max_subtasks} subtasks\n"
        "- Each query must be SPECIFIC and TARGETED — never repeat the goal verbatim\n"
        "- Queries should cover DIFFERENT ASPECTS (definitions, comparisons, recent developments, use cases, challenges)\n"
        "- Use natural-language search queries as if searching Google\n"
        "- Include at least one query about recent developments (add 'latest' or '2024' or '2025')\n"
        "- Include at least one query that compares or contrasts alternatives\n"
        "- Each subtask can list dependencies (IDs of tasks that must finish first)\n\n"

        f"## Available Tools\n{tools_section}\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a valid JSON array:\n"
        '[{"title": "short title", "query": "specific detailed search query with keywords", '
        '"description": "what this task investigates and why", "tool_hint": "web_search", '
        '"dependencies": []}]\n\n'

        "## Quality Criteria\n"
        "- Each subtask must investigate a distinct aspect of the goal\n"
        "- Queries must be specific enough to return targeted results\n"
        "- Dependencies should reflect logical ordering (e.g., definitions before comparisons)\n"
        "- Good coverage: breadth (multiple angles) + depth (specific queries)"
        + goal_context
        + memory_section
    ))
    human = HumanMessage(content=f"Goal: {goal}")

    # Check Redis cache for this planning request
    max_tasks = 3 if mode == 'fast' else 10
    cache_key_data = f"plan:{goal}:{mode}"
    cached = await get_cached("planner", cache_key_data)
    if cached:
        subtasks = _parse_subtasks(cached, max_tasks)
    else:
        response = await llm.ainvoke([system, human])
        await set_cached("planner", cache_key_data, response.content, ttl=LLM_CACHE_TTL)
        subtasks = _parse_subtasks(response.content, max_tasks)

    duration_ms = int((time.time() - start_time) * 1000)

    await _emit({
        "type": "plan_ready",
        "node": "planner",
        "subtasks": subtasks,
    })
    
    # Save subtasks to the database
    try:
        await save_subtasks(state.get("run_id"), subtasks)
    except Exception as e:
        logger.warning(f"Failed to save subtasks to DB: {e}")

    await _emit({
        "type": "node_done",
        "node": "planner",
        "duration_ms": duration_ms,
    })

    timings = dict(state.get("node_timings", {}))
    timings["planner"] = duration_ms

    return {
        "subtasks": subtasks,
        "current_idx": 0,
        "memory_context": memory_context,
        "node_timings": timings,
    }
