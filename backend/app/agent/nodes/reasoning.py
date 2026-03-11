"""
Reasoning Node — Explicit reasoning stage between data collection and synthesis.
Analyzes collected evidence, identifies patterns, detects contradictions,
and derives preliminary conclusions.
"""
import json
import re
import time
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import ARIAState, ReasoningOutput
from ..context import get_queue, check_pause_and_abort
from ...llm import get_llm
from ...logger import get_logger

logger = get_logger(__name__)


async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)


async def reasoning_node(state: ARIAState) -> dict:
    """Advanced reasoning: Detect contradictions and synthesize insights."""
    await check_pause_and_abort(state.get("run_id"))
    goal = state["goal"]
    evidence = state.get("extracted_evidence", [])
    kg = state.get("knowledge_graph", [])
    hypotheses = state.get("hypotheses", [])
    debate_log = state.get("debate_log", [])
    start_time = time.time()

    await _emit({
        "type": "node_start",
        "node": "reasoning",
        "label": "Analyzing evidence & contradictions...",
    })

    if not evidence and not kg:
        return {"reasoning_output": {}, "node_timings": {**state.get("node_timings", {}), "reasoning": 0}}

    llm = get_llm(streaming=False, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Advanced Reasoning Engine. Your duty is to perform deep "
        "logical analysis, detect contradictions, and synthesize cross-dimensional insights.\n\n"

        "## Task\n"
        "Analyze the evidence, knowledge graph, hypotheses, and the debate log. "
        "Produce a structured analytical summary that will be used for the final report.\n\n"

        "## Analytical Dimensions\n"
        "1. **Contradiction Detection**: Explicitly identify conflicting claims across sources.\n"
        "2. **Evidence Normalization**: Reconcile different data points.\n"
        "3. **Insight Synthesis**: Connect disparate facts into high-level findings.\n"
        "4. **Gap Analysis**: Identify what is still unknown or uncertain.\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON object:\n"
        '{\n'
        '  "evidence_summary": "High-level overview of the evidence landscape",\n'
        '  "patterns": ["Significant trends or relationships discovered"],\n'
        '  "contradictions": ["Conflicting claims with source references"],\n'
        '  "conclusions": ["Validated conclusions backed by the debate and evidence"],\n'
        '  "confidence_score": 8.5,\n'
        '  "gaps": ["Unresolved questions or missing data points"]\n'
        '}'
    ))

    human = HumanMessage(content=(
        f"**Research Goal:** {goal}\n\n"
        f"**Extracted Evidence:** {json.dumps(evidence[:30], indent=2)}\n\n"
        f"**Knowledge Graph:** {json.dumps(kg, indent=2)}\n\n"
        f"**Proposed Hypotheses:** {json.dumps(hypotheses, indent=2)}\n\n"
        f"**Debate Log:** {json.dumps(debate_log, indent=2)}"
    ))

    response = await llm.ainvoke([system, human])
    
    reasoning = {}
    try:
        # Extract JSON from response
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if match:
            reasoning = json.loads(match.group())
        else:
            reasoning = json.loads(response.content)
    except Exception as e:
        logger.warning(f"Failed to parse reasoning output as JSON: {e}")
        reasoning = {
            "evidence_summary": response.content[:500],
            "patterns": [],
            "contradictions": [],
            "conclusions": [],
            "confidence_score": 5.0,
            "gaps": []
        }

    duration_ms = int((time.time() - start_time) * 1000)

    await _emit({
        "type": "reasoning_complete",
        "node": "reasoning",
        "reasoning": reasoning,
        "duration_ms": duration_ms,
    })
    await _emit({
        "type": "node_done",
        "node": "reasoning",
        "duration_ms": duration_ms,
    })

    timings = dict(state.get("node_timings", {}))
    timings["reasoning"] = duration_ms

    return {
        "reasoning_output": reasoning,
        "node_timings": timings,
    }
