"""Routing helpers for the LangGraph pipeline."""
from ..state import ARIAState


def should_continue_executing(state: ARIAState) -> str:
    """Route: keep executing subtasks, or move to memory storage."""
    subtasks = state.get("subtasks", [])

    # Check if there are still pending tasks
    pending = [st for st in subtasks if st["status"] == "pending"]
    if pending:
        return "execute"
    return "store_memory"
