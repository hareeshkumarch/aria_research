"""
ARIA LangGraph Pipeline — Multi-loop architecture with full reasoning chain.

Pipeline topology:
  START → goal_understanding → planner → executor ─┐
                                         ↑         │ (loops until all subtasks done)
                                         └─────────┘
                                                   └→ memory_node → reasoning → synthesizer → critic ─┐
                                                                                    ↑                  │
                                                                                    └── refiner ←──────┘ (if score < 7)
                                                                                                       │
                                                                                                       └→ END (if score ≥ 7)

Execution stages:
  1. Goal Understanding — parse intent, entities, scope
  2. Planning — decompose into subtask DAG
  3. Execution — run tools for each subtask (loop)
  4. Memory — store findings in ChromaDB
  5. Reasoning — analyze evidence, find patterns, detect contradictions
  6. Synthesis — write polished report using reasoning output
  7. Critique — score quality across dimensions
  8. Refinement — targeted re-research if quality is low (loop)
"""
import asyncio
from langgraph.graph import StateGraph, END, START

from .state import ARIAState
from .context import (
    set_queue,
    set_cost_tracker,
    set_run_id,
    register_run_controls,
    unregister_run_controls,
)
from ..logger import get_logger
from .cost import CostTracker
from .nodes.goal_understanding import goal_understanding_node
from .nodes.planner import planner_node
from .nodes.strategy_generator import strategy_generator_node
from .nodes.executor import executor_node
from .nodes.source_validator import source_validator_node
from .nodes.evidence_extractor import evidence_extractor_node
from .nodes.normalizer import normalizer_node
from .nodes.kg_builder import kg_builder_node
from .nodes.hypothesis_generator import hypothesis_generator_node
from .nodes.debate_system import debate_system_node
from .nodes.reasoning import reasoning_node  # Will handle 12 (Contradictions) and 14 (Insights)
from .nodes.refiner import refiner_node     # 13 (Re-Query Loop)
from .nodes.synthesizer import synthesizer_node # 16 (Report)
from .nodes.critic import critic_node, route_after_critic # 15 (Confidence)
from .nodes.memory_node import memory_node   # 17 (Memory)
from .nodes.router import should_continue_executing


def build_graph():
    """Build the ARIA V2 Consolidated 8-stage pipeline."""
    workflow = StateGraph(ARIAState)

    # ─── Macro-Nodes ──────────────────────────────────────────
    
    async def intake_node(state: ARIAState) -> dict:
        return await goal_understanding_node(state)

    async def planning_node(state: ARIAState) -> dict:
        s1 = await planner_node(state)
        # Update state partially for the next step within the same macro-node
        temp_state = {**state, **s1}
        s2 = await strategy_generator_node(temp_state)
        return {**s1, **s2}

    async def research_node(state: ARIAState) -> dict:
        # Entry point for executor loop
        return await executor_node(state)

    async def analysis_node(state: ARIAState) -> dict:
        # Consolidation of validation, extraction, normalization, and building
        s1 = await source_validator_node(state)
        state = {**state, **s1}
        s2 = await evidence_extractor_node(state)
        state = {**state, **s2}
        s3 = await normalizer_node(state)
        state = {**state, **s3}
        s4 = await kg_builder_node(state)
        state = {**state, **s4}
        s5 = await hypothesis_generator_node(state)
        state = {**state, **s5}
        s6 = await debate_system_node(state)
        return {**s1, **s2, **s3, **s4, **s5, **s6}

    async def review_node(state: ARIAState) -> dict:
        # Handles critic logic
        return await critic_node(state)

    # ─── Add Nodes ────────────────────────────────────────────
    workflow.add_node("intake", intake_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("research", research_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("synthesis", synthesizer_node)
    workflow.add_node("review", review_node)
    workflow.add_node("memory", memory_node)
    workflow.add_node("refiner", refiner_node) # Bridge node for refinement logic

    # ─── Edges ────────────────────────────────────────────────
    workflow.add_edge(START, "intake")
    workflow.add_edge("intake", "planning")
    workflow.add_edge("planning", "research")

    # Research Loop
    workflow.add_conditional_edges(
        "research",
        should_continue_executing,
        {
            "execute": "research",
            "store_memory": "analysis",
        },
    )

    workflow.add_edge("analysis", "reasoning")
    workflow.add_edge("reasoning", "synthesis")
    workflow.add_edge("synthesis", "review")

    # Review/Refinement Loop
    workflow.add_conditional_edges(
        "review",
        route_after_critic,
        {
            "refine": "refiner",
            "done": "memory",
        },
    )

    workflow.add_edge("refiner", "planning")
    workflow.add_edge("memory", END)

    return workflow.compile()


# Single compiled graph instance
aria_graph = build_graph()
logger = get_logger(__name__)

async def run_agent(goal: str, run_id: str, queue: asyncio.Queue, mode: str = "fast", model: str | None = None, provider: str | None = None):
    """Entry point: run ARIA agent."""
    set_queue(queue)
    set_run_id(run_id)
    # Create per-run cost tracker so the UI can update live via callbacks.
    set_cost_tracker(CostTracker(provider or "auto", model or "auto"))
    pause_event = asyncio.Event()
    pause_event.set()
    register_run_controls(run_id, pause_event)

    initial_state: ARIAState = {
        "goal": goal,
        "run_id": run_id,
        "mode": mode,
        "model": model,
        "provider": provider,
        "goal_analysis": {},
        "subtasks": [],
        "current_idx": 0,
        "tool_results": [],
        "research_strategy": "",
        "validated_sources": [],
        "extracted_evidence": [],
        "knowledge_graph": [],
        "hypotheses": [],
        "debate_log": [],
        "contradictions": [],
        "confidence_score": 0.0,
        "memory_context": [],
        "reasoning_output": {},
        "draft_output": "",
        "final_output": "",
        "critic_score": 0.0,
        "critic_feedback": "",
        "retry_count": 0,
        "cost_data": {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0},
        "node_timings": {},
        "error_detail": "",
    }

    try:
        await queue.put({"type": "run_start", "run_id": run_id, "goal": goal})
        # Set recursion limit to 250 for extreme headroom
        result = await aria_graph.ainvoke(initial_state, config={"recursion_limit": 250})

        await queue.put({
            "type": "run_complete",
            "output": result.get("final_output", ""),
            "critic_score": result.get("critic_score", 0),
            "cost_data": result.get("cost_data", {}),
            "node_timings": result.get("node_timings", {}),
        })

    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        await queue.put({"type": "run_error", "error": f"{type(e).__name__}: {str(e)}"})
    finally:
        unregister_run_controls(run_id)
