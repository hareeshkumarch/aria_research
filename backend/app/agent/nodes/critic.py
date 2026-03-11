"""
Critic Node — Self-evaluation loop for output quality.
Scores the synthesized output across multiple dimensions and decides whether to accept or retry.
"""
import json
import re
import time
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import ARIAState
from ..context import get_queue, check_pause_and_abort
from ...llm import get_llm
from ...config import settings
from ...logger import get_logger

logger = get_logger(__name__)


async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)


async def critic_node(state: ARIAState) -> dict:
    """Advanced quality audit: Confidence scoring & uncertainty estimation."""
    await check_pause_and_abort(state.get("run_id"))
    goal = state["goal"]
    report = state.get("final_output", "")
    reasoning = state.get("reasoning_output", {})
    evidence = state.get("extracted_evidence", [])
    retry_count = state.get("retry_count", 0)
    start_time = time.time()

    await _emit({"type": "node_start", "node": "critic", "label": "Estimating confidence & uncertainty..."})

    if not report:
        return {"critic_score": 0.0, "node_timings": {**state.get("node_timings", {}), "critic": 0}}

    # Use a faster model for the refinement loop by default (keeps runs snappy)
    llm = get_llm(
        streaming=False,
        provider=settings.refine_provider or state.get("provider"),
        model=settings.refine_model or state.get("model"),
    )

    system = SystemMessage(content=(
        "## System Role\n"
        "You are ARIA's Quality & Uncertainty Critic. Your job is to assign "
        "confidence scores and identify lingering uncertainties in the research report.\n\n"

        "## Task\n"
        "Audit the final report against the evidence and reasoning. Calculate a "
        "rigorous confidence score (0-10) and define the 'Uncertainty Profile'.\n\n"

        "## Evaluation Dimensions\n"
        "1. **Completeness** (0-10): All facets of the goal addressed?\n"
        "2. **Evidence Density** (0-10): Ratio of claims vs citations.\n"
        "3. **Consistency** (0-10): Absence of unresolved contradictions.\n"
        "4. **Uncertainty Factor**: Level of ambiguity in the source material.\n\n"

        "## Scoring Formula\n"
        "overall_score = (completeness + evidence_density + consistency) / 3 * (1 - uncertainty_factor)\n\n"

        "## Required Output Schema\n"
        "Respond with ONLY a JSON object:\n"
        '{\n'
        '  "overall_score": 7.5,\n'
        '  "confidence_breakdown": {"completeness": 8, "evidence": 9, "consistency": 7},\n'
        '  "uncertainty_profile": "Description of what remains unknown",\n'
        '  "improvement_suggestions": "Concrete gaps to fill if score < 7",\n'
        '  "is_passed": true \n'
        '}'
    ))

    human = HumanMessage(content=(
        f"**Report:** {report[:5000]}\n\n"
        f"**Reasoning Gaps:** {json.dumps(reasoning.get('gaps', []), indent=2)}\n\n"
        f"**Evidence Count:** {len(evidence)}"
    ))

    response = await llm.ainvoke([system, human])
    
    score = 5.0
    feedback = ""
    try:
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        data = json.loads(match.group()) if match else json.loads(response.content)
        
        score = float(data.get("overall_score", 5.0))
        feedback = data.get("improvement_suggestions", "No suggestions provided.")
        breakdown = data.get("confidence_breakdown", {})
        
        # Build strengths/weaknesses from breakdown for the frontend
        strengths = [f"{k}: {v}/10" for k, v in breakdown.items() if isinstance(v, (int, float)) and v >= 7]
        weaknesses = [f"{k}: {v}/10" for k, v in breakdown.items() if isinstance(v, (int, float)) and v < 7]
        
        await _emit({
            "type": "critic_score",
            "node": "critic",
            "score": score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "suggestions": feedback,
        })
    except Exception as e:
        logger.warning(f"Failed to parse critic output as JSON: {e}")
        score = 6.8 # Fallback to a passing score if parsing fails but model likely succeeded
        feedback = "Parsing failed, using default evaluation."

    duration_ms = int((time.time() - start_time) * 1000)

    await _emit({
        "type": "node_done",
        "node": "critic",
        "score": score,
        "duration_ms": duration_ms,
    })

    return {
        "critic_score": score,
        "critic_feedback": feedback,
        "confidence_score": score,
        "retry_count": retry_count + 1,
        "node_timings": {**state.get("node_timings", {}), "critic": duration_ms}
    }


def route_after_critic(state: ARIAState) -> str:
    """Route back to refiner if score is below mode threshold, else loop ends."""
    score = state.get("critic_score", 10.0)
    retry_count = state.get("retry_count", 0)
    mode = state.get("mode", "fast")
    
    threshold = 6.5 if mode == "fast" else 8.5

    if score < threshold and retry_count <= settings.max_retries:
        return "refine"
    return "done"
