"""Memory tools — recall and store using ChromaDB.

Errors are logged via the shared logger but surfaced back to the agent as simple
strings to keep the tool contract consistent.
"""
import time

from ...memory.chroma import memory_service
from ...logger import get_logger

logger = get_logger(__name__)


async def recall_memory(query: str, n_results: int = 5) -> tuple[str, int]:
    """
    Search ARIA's memory for relevant past findings.
    Returns (formatted_memories, duration_ms).
    """
    start = time.time()
    try:
        memories = await memory_service.retrieve(query, n_results=n_results)

        if not memories:
            return "No relevant memories found.", int((time.time() - start) * 1000)

        parts = []
        for m in memories:
            relevance = m.get("relevance", 0)
            source = m.get("metadata", {}).get("source", "unknown")
            parts.append(
                f"**[Memory — {source}, relevance: {relevance:.2f}]**\n{m['text']}"
            )

        duration_ms = int((time.time() - start) * 1000)
        return "\n\n---\n\n".join(parts), duration_ms

    except Exception as e:
        logger.error("Memory recall failed for query '%s': %s", query, str(e))
        return f"Memory recall failed: {str(e)}", 0


async def store_memory(
    text: str,
    run_id: str,
    source: str = "agent",
    goal: str = "",
    importance: float = 0.5,
) -> tuple[str, int]:
    """
    Store a finding in ARIA's persistent memory.
    Returns (status_message, duration_ms).
    """
    start = time.time()
    try:
        chunk_id = await memory_service.store(
            text=text,
            run_id=run_id,
            source=source,
            goal=goal,
            importance=importance,
        )
        duration_ms = int((time.time() - start) * 1000)
        return f"Stored to memory (id: {chunk_id})", duration_ms

    except Exception as e:
        logger.error("Memory store failed for run_id '%s': %s", run_id, str(e))
        return f"Memory store failed: {str(e)}", 0
