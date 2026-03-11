"""
Evidence Extractor Node — Pulls specific facts/quotes from sources.
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

async def evidence_extractor_node(state: ARIAState) -> dict:
    """Extract atomic facts and evidence from research results."""
    await check_pause_and_abort(state.get("run_id"))
    subtasks = state.get("subtasks", [])
    start_time = time.time()

    await _emit({"type": "node_start", "node": "evidence_extractor", "label": "Extracting atomic facts..."})

    # Collect all search results
    raw_data = []
    for st in subtasks:
        if st.get("result"):
            raw_data.append(f"Source: {st.get('query')}\nContent: {st['result'][:2000]}")

    if not raw_data:
        return {"extracted_evidence": [], "node_timings": {**state.get("node_timings", {}), "evidence_extractor": 0}}

    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Evidence Extraction Engine. Your job is to pull specific, "
        "verifiable atomic facts and quotes from raw research data.\n\n"

        "## Task\n"
        "Analyze the provided search data and extract high-confidence facts. "
        "Each fact must be 'atomic' (one distinct piece of information) and linked to its source.\n\n"

        "## Constraints\n"
        "- Only extract information that is explicitly stated.\n"
        "- Provide a confidence score (0.0 - 1.0) for each fact based on clarity and source reputation.\n"
        "- Include the original context (a short snippet).\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON object containing a list of `extracted_evidence`:\n"
        '{\n'
        '  "extracted_evidence": [\n'
        '    {\n'
        '      "fact": "Specific verifiable fact",\n'
        '      "source_url": "URL or search query identifier",\n'
        '      "confidence": 0.95,\n'
        '      "context": "Short snippet from the source text"\n'
        '    }\n'
        '  ]\n'
        '}'
    ))

    human = HumanMessage(content="Raw Research Data:\n\n" + "\n---\n".join(raw_data))

    response = await llm.ainvoke([system, human])
    
    try:
        data = json.loads(response.content)
        extracted_evidence = data.get("extracted_evidence", [])
    except Exception as e:
        logger.error(f"Failed to parse Evidence Extractor JSON: {e}")
        extracted_evidence = []
    
    duration_ms = int((time.time() - start_time) * 1000)
    await _emit({"type": "node_done", "node": "evidence_extractor", "duration_ms": duration_ms})

    return {
        "extracted_evidence": extracted_evidence,
        "node_timings": {**state.get("node_timings", {}), "evidence_extractor": duration_ms}
    }
