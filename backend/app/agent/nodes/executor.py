"""
Executor Node — Runs tools for each subtask with retry + multi-tool support.
Respects DAG dependencies — only executes tasks whose deps are complete.
Validates tool responses before accepting results.
"""
import asyncio
import time

from ..state import ARIAState
from ..context import get_queue, check_pause_and_abort
from ..tools.registry import get_tool, is_tool_available, validate_tool_result
from ...config import settings
from ...repositories.events_repo import save_tool_call
from ...logger import get_logger
from ...cache import get_cached, set_cached, SEARCH_CACHE_TTL

logger = get_logger(__name__)


async def _emit(event: dict):
    queue = get_queue()
    if queue:
        await queue.put(event)


async def _execute_tool(tool_name: str, subtask: dict, run_id: str) -> tuple[str, int]:
    """Execute a tool with the appropriate arguments."""
    tool_fn = get_tool(tool_name)
    if not tool_fn:
        return f"Unknown tool: {tool_name}", 0

    if tool_name == "web_search":
        # Check Redis cache for this search query
        cached = await get_cached("search", subtask["query"])
        if cached:
            return cached, 0
        result, dur = await tool_fn(subtask["query"], max_results=5)
        if isinstance(result, str) and len(result) > 50:
            await set_cached("search", subtask["query"], result, ttl=SEARCH_CACHE_TTL)
        return result, dur
    elif tool_name == "web_fetch":
        return await tool_fn(subtask["query"])
    elif tool_name == "recall_memory":
        return await tool_fn(subtask["query"])
    elif tool_name == "store_memory":
        return await tool_fn(subtask.get("result", ""), run_id=run_id, goal=subtask.get("query", ""))
    elif tool_name == "code_exec":
        return await tool_fn(subtask["query"])
    elif tool_name == "read_file":
        return await tool_fn(subtask["query"])
    elif tool_name == "write_file":
        return await tool_fn(subtask["query"], subtask.get("description", ""))
    else:
        return f"Tool '{tool_name}' not implemented", 0


def _get_ready_subtasks(subtasks: list) -> list[tuple[int, dict]]:
    """Find all subtasks that are ready to execute (deps satisfied)."""
    completed_ids = {st["id"] for st in subtasks if st["status"] in ["done", "failed"]}
    
    ready = []
    for i, st in enumerate(subtasks):
        if st["status"] != "pending":
            continue
            
        deps = st.get("dependencies", [])
        if all(d in completed_ids for d in deps):
            ready.append((i, st))
            
    return ready


async def _execute_single_subtask(task_idx: int, subtask: dict, run_id: str) -> tuple[int, dict, str]:
    """Execute a single subtask with retry logic and response validation."""
    node_id = f"subtask_{subtask['id']}"
    subtask_start = time.time()

    await _emit({
        "type": "node_start",
        "node": node_id,
        "label": subtask["title"],
        "subtask_id": subtask["id"],
    })

    tool_name = subtask.get("tool_hint", "web_search")
    if not is_tool_available(tool_name):
        tool_name = "web_search"

    await _emit({
        "type": "tool_call",
        "node": node_id,
        "tool": tool_name,
        "query": subtask["query"],
    })

    result = ""
    duration_ms = 0
    success = False

    for attempt in range(settings.max_retries + 1):
        try:
            # Enforce strict 20s timeout per tool call
            result, duration_ms = await asyncio.wait_for(
                _execute_tool(tool_name, subtask, run_id), timeout=20.0
            )

            # Enforce max 4000 chars for tool result to prevent memory bloat
            if isinstance(result, str) and len(result) > 4000:
                result = result[:4000] + "\n\n...[Content truncated due to length]..."
            
            # Validate the tool response
            is_valid, validation_msg = validate_tool_result(tool_name, result)
            
            if not is_valid:
                logger.warning(f"[{node_id}] Tool validation failed on attempt {attempt+1}: {validation_msg}")
                if attempt < settings.max_retries:
                    await _emit({
                        "type": "tool_retry",
                        "node": node_id,
                        "attempt": attempt + 1,
                        "reason": f"Validation failed: {validation_msg}",
                    })
                    await asyncio.sleep(2 ** attempt)
                    continue
            
            success = True
            break

        except asyncio.TimeoutError:
            logger.error(f"[{node_id}] Tool execution timed out after 20s")
            result = "Tool execution timed out."
            if attempt < settings.max_retries:
                await _emit({
                    "type": "tool_retry",
                    "node": node_id,
                    "attempt": attempt + 1,
                    "reason": "Timeout exceeded",
                })
                await asyncio.sleep(2 ** attempt)
            else:
                success = False

        except Exception as e:
            logger.error(f"[{node_id}] Tool execution error ({type(e).__name__}): {e}")
            result = f"Tool error ({type(e).__name__}): {str(e)}"
            if attempt < settings.max_retries:
                await _emit({
                    "type": "tool_retry",
                    "node": node_id,
                    "attempt": attempt + 1,
                    "reason": str(e),
                })
                await asyncio.sleep(2 ** attempt)
            else:
                success = False

    total_duration = int((time.time() - subtask_start) * 1000)

    updated = dict(subtask)
    updated["status"] = "done" if success else "failed"
    updated["result"] = result
    updated["retry_count"] = subtask.get("retry_count", 0) + (1 if not success else 0)

    # Save tool call to the database
    try:
        await save_tool_call(
            run_id=run_id,
            subtask_id=f"{run_id}_{subtask['id']}",
            tool_name=tool_name,
            input_data=subtask["query"],
            output_data=result,
            success=success,
            duration_ms=total_duration
        )
    except Exception as e:
        logger.warning(f"Failed to save tool call to DB: {e}")

    await _emit({
        "type": "node_done",
        "node": node_id,
        "subtask_id": subtask["id"],
        "result_preview": result[:150] + "..." if len(result) > 150 else result,
        "duration_ms": total_duration,
        "success": success,
    })

    tool_result_str = f"## {subtask['title']}\n\n{result}"
    return task_idx, updated, tool_result_str


async def executor_node(state: ARIAState) -> dict:
    """Execute next ready subtasks concurrently."""
    # Check pause/abort before starting execution
    await check_pause_and_abort(state.get("run_id"))

    subtasks = list(state["subtasks"])
    run_id = state["run_id"]
    start_time = time.time()

    # Find ALL ready subtasks
    ready_tasks = _get_ready_subtasks(subtasks)
    
    if not ready_tasks:
        # All done or stuck
        return {"current_idx": len(subtasks)}

    # Execute them concurrently
    coroutines = [
        _execute_single_subtask(idx, st, run_id)
        for idx, st in ready_tasks
    ]
    
    results = await asyncio.gather(*coroutines)
    
    new_tool_results = []
    # Update state with results
    for task_idx, updated_subtask, tool_result_str in results:
        subtasks[task_idx] = updated_subtask
        new_tool_results.append(tool_result_str)

    # Calculate next_idx based on remaining pending tasks
    next_idx = 0
    for i, st in enumerate(subtasks):
        if st["status"] == "pending":
            next_idx = i
            break
    else:
        next_idx = len(subtasks)

    duration_ms = int((time.time() - start_time) * 1000)

    timings = dict(state.get("node_timings", {}))
    timings["executor"] = timings.get("executor", 0) + duration_ms

    await _emit({
        "type": "node_done",
        "node": "executor",
        "duration_ms": duration_ms,
    })

    return {
        "subtasks": subtasks,
        "current_idx": next_idx,
        "tool_results": new_tool_results,
        "node_timings": timings,
    }
