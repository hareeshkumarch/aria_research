"""
Source Validator Node — Scores credibility and relevance of found URLs.
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

async def source_validator_node(state: ARIAState) -> dict:
    """Evaluate and score the credibility of discovered sources."""
    await check_pause_and_abort(state.get("run_id"))
    subtasks = state.get("subtasks", [])
    start_time = time.time()

    await _emit({"type": "node_start", "node": "source_validator", "label": "Evaluating source credibility..."})

    # Collect all results that have search content
    search_data = []
    for st in subtasks:
        if st.get("result") and st.get("tool_hint") == "web_search":
            search_data.append(f"Query: {st['query']}\nResult: {st['result'][:1000]}")

    if not search_data:
        return {"validated_sources": [], "node_timings": {**state.get("node_timings", {}), "source_validator": 0}}

    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Source Validator. Your job is to evaluate the "
        "credibility and relevance of discovered research sources.\n\n"

        "## Task\n"
        "Analyze the provided search results. Identify the key sources (URLs) and "
        "assign a credibility score (0-10) and a relevance score (0-10) to each.\n\n"

        "## Scoring Criteria\n"
        "- **Credibility**: Higher for official sites (.gov, .edu), reputable news (Reuters, NYT), "
        "and primary research. Lower for personal blogs, social media, or known biased sources.\n"
        "- **Relevance**: How well the source addresses the specific research query.\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON object containing a list of `validated_sources`:\n"
        '{\n'
        '  "validated_sources": [\n'
        '    {\n'
        '      "url": "https://example.com/article",\n'
        '      "title": "Article Title",\n'
        '      "credibility_score": 8.5,\n'
        '      "relevance_score": 9.0,\n'
        '      "rationale": "High credibility due to being an official gov site."\n'
        '    }\n'
        '  ]\n'
        '}'
    ))

    human = HumanMessage(content="Search Results:\n\n" + "\n---\n".join(search_data))

    response = await llm.ainvoke([system, human])
    
    try:
        data = json.loads(response.content)
        validated_sources = data.get("validated_sources", [])
    except Exception as e:
        logger.error(f"Failed to parse Source Validator JSON: {e}")
        validated_sources = []
    
    duration_ms = int((time.time() - start_time) * 1000)
    await _emit({"type": "node_done", "node": "source_validator", "duration_ms": duration_ms})

    return {
        "validated_sources": validated_sources,
        "node_timings": {**state.get("node_timings", {}), "source_validator": duration_ms}
    }
