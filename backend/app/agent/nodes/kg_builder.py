"""
Knowledge Graph Builder Node — Maps relationships between entities.
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

async def kg_builder_node(state: ARIAState) -> dict:
    """Build a knowledge graph from extracted evidence."""
    await check_pause_and_abort(state.get("run_id"))
    evidence = state.get("extracted_evidence", [])
    start_time = time.time()

    await _emit({"type": "node_start", "node": "kg_builder", "label": "Mapping entity relationships..."})

    if not evidence:
        return {"knowledge_graph": [], "node_timings": {**state.get("node_timings", {}), "kg_builder": 0}}

    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Knowledge Graph Builder. Your job is to identify "
        "connections between entities and concepts discovered in the research.\n\n"

        "## Task\n"
        "Analyze the extracted evidence and create a knowledge graph. Identify entities "
        "and the relationships between them.\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON object containing a list called `knowledge_graph`:\n"
        '{\n'
        '  "knowledge_graph": [\n'
        '    {\n'
        '      "source": "Entity A",\n'
        '      "target": "Entity B",\n'
        '      "relationship": "type of relationship",\n'
        '      "evidence": ["supporting fact 1"]\n'
        '    }\n'
        '  ]\n'
        '}'
    ))

    human = HumanMessage(content=f"Normalized Evidence:\n\n{json.dumps(evidence, indent=2)}")

    response = await llm.ainvoke([system, human])
    
    try:
        data = json.loads(response.content)
        knowledge_graph = data.get("knowledge_graph", [])
    except Exception as e:
        logger.error(f"Failed to parse KG Builder JSON: {e}")
        knowledge_graph = []
    
    duration_ms = int((time.time() - start_time) * 1000)
    await _emit({"type": "node_done", "node": "kg_builder", "duration_ms": duration_ms})

    return {
        "knowledge_graph": knowledge_graph,
        "node_timings": {**state.get("node_timings", {}), "kg_builder": duration_ms}
    }
