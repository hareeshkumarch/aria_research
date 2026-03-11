"""
Synthesizer Node — Combines research findings and reasoning output into a polished report.
Streams tokens via SSE. Uses reasoning conclusions for higher-quality synthesis.
"""
import time
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import ARIAState
from ..context import get_queue, check_pause_and_abort
from ...llm import get_llm
from ...logger import get_logger

logger = get_logger(__name__)


async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)


import json

async def synthesizer_node(state: ARIAState) -> dict:
    """Advanced synthesis: Generate research-grade report."""
    await check_pause_and_abort(state.get("run_id"))
    goal = state["goal"]
    mode = state.get("mode", "fast")
    evidence = state.get("extracted_evidence", [])
    kg = state.get("knowledge_graph", [])
    hypotheses = state.get("hypotheses", [])
    debate_log = state.get("debate_log", [])
    reasoning = state.get("reasoning_output", {})
    start_time = time.time()

    await _emit({"type": "node_start", "node": "synthesizer", "label": "Generating final research report..."})

    llm = get_llm(streaming=True, provider=state.get("provider"), model=state.get("model"))

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Final Research Report Generator — the lead analyst tasked "
        "with producing the definitive document on the research goal.\n\n"

        "## Task\n"
        "Synthesize all evidence, knowledge graphs, hypotheses, and analytical reasoning "
        "into a comprehensive, professional research report.\n\n"

        "## Constraints\n"
        "- **Breadth & Depth**: " + ("Aim for 1500+ words in Deep Mode." if mode != "fast" else "Aim for 600 words in Fast Mode.") + "\n"
        "- **Evidence-First**: Every factual claim must cite a source from the provided evidence.\n"
        "- **Analytical Rigor**: Include insights from the KG and the multi-agent debate.\n\n"

        "## Required Output Format (Markdown)\n"
        "1. **Executive Summary**: Core findings.\n"
        "2. **Research Methodology**: Overview of synthesis.\n"
        "3. **Key Findings**: Detailed thematic sections with inline citations.\n"
        "4. **Technical Landscape / Knowledge Graph**: Discussion of entity relationships.\n"
        "5. **Hypothesis Evaluation**: Discussion of hypotheses and debate results.\n"
        "6. **Contradictions & Gaps**: Explicit section on conflicting data.\n"
        "7. **Actionable Recommendations**: Next steps.\n"
        "8. **Conclusion & Confidence Statement**."
    ))

    human = HumanMessage(content=(
        f"**Goal:** {goal}\n\n"
        f"**Reasoning Analysis:** {json.dumps(reasoning, indent=2)}\n\n"
        f"**Knowledge Graph:** {json.dumps(kg[:10], indent=2)}\n\n"
        f"**Hypotheses & Debate:** {json.dumps(debate_log, indent=2)}\n\n"
        f"**Verified Evidence:** {json.dumps(evidence[:40], indent=2)}"
    ))

    full_output = ""
    async for chunk in llm.astream([system, human]):
        if chunk.content:
            full_output += chunk.content
            await _emit({"type": "token", "content": chunk.content})

    duration_ms = int((time.time() - start_time) * 1000)
    await _emit({"type": "node_done", "node": "synthesizer", "duration_ms": duration_ms})

    return {
        "final_output": full_output,
        "draft_output": full_output,
        "node_timings": {**state.get("node_timings", {}), "synthesizer": duration_ms}
    }
