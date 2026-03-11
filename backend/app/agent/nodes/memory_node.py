"""
Memory Node — Stores tool results in ChromaDB after execution.
This creates persistent knowledge that future runs can retrieve.
"""
import time
from ..state import ARIAState
from ..context import get_queue, check_pause_and_abort
from ...memory.chroma import memory_service


async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)


async def memory_node(state: ARIAState) -> dict:
    """Store completed subtask results in ChromaDB."""
    await check_pause_and_abort(state.get("run_id"))
    subtasks = state.get("subtasks", [])
    goal = state["goal"]
    run_id = state["run_id"]
    start_time = time.time()

    await _emit({"type": "node_start", "node": "memory", "label": "Storing findings to memory..."})

    stored_count = 0
    for st in subtasks:
        if st["status"] == "done" and st.get("result"):
            try:
                # Score importance based on result quality
                importance = 0.6 if len(st["result"]) > 200 else 0.4

                await memory_service.store(
                    text=f"## {st['title']}\n\n{st['result'][:2000]}",
                    run_id=run_id,
                    source="executor",
                    goal=goal,
                    importance=importance,
                )
                stored_count += 1
            except Exception:
                pass  # Memory is best-effort

    duration_ms = int((time.time() - start_time) * 1000)

    await _emit({
        "type": "memory_store",
        "node": "memory",
        "count": stored_count,
        "message": f"Stored {stored_count} findings to long-term memory",
    })
    await _emit({
        "type": "node_done",
        "node": "memory",
        "duration_ms": duration_ms,
    })

    timings = dict(state.get("node_timings", {}))
    timings["memory"] = duration_ms

    return {
        "current_idx": state.get("current_idx", 0),
        "node_timings": timings,
    }
