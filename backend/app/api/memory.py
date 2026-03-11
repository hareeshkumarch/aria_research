"""Memory API — browse, search, and manage ARIA's persistent memory."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..memory.chroma import memory_service
from ..logger import get_logger


router = APIRouter()
logger = get_logger(__name__)


class MemoryQueryRequest(BaseModel):
    query: str
    n_results: int = 5
    min_importance: float = 0.3


class MemoryChunkResponse(BaseModel):
    id: str
    text: str
    metadata: dict


@router.get("/memory")
async def list_memory(limit: int = 100):
    """List all memory chunks."""
    try:
        memories = await memory_service.list_all(limit=limit)
        return {"memories": memories, "total": len(memories)}
    except Exception as e:
        logger.error(f"Failed to list memory: {e}")
        return {"memories": [], "total": 0, "error": str(e)}


@router.post("/memory/query")
async def query_memory(body: MemoryQueryRequest):
    """Semantic search through ARIA's memory."""
    try:
        results = await memory_service.retrieve(
            query=body.query,
            n_results=body.n_results,
            min_importance=body.min_importance,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Failed to query memory: {e}")
        return {"results": [], "count": 0, "error": str(e)}


@router.delete("/memory/{chunk_id}")
async def delete_memory_chunk(chunk_id: str):
    """Delete a specific memory chunk."""
    try:
        await memory_service.forget(chunk_id)
        return {"message": f"Memory chunk {chunk_id} deleted."}
    except Exception as e:
        logger.error(f"Failed to delete memory chunk {chunk_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/run/{run_id}")
async def delete_run_memory(run_id: str):
    """Delete all memory from a specific run."""
    try:
        await memory_service.forget_by_run(run_id)
        return {"message": f"All memory from run {run_id} deleted."}
    except Exception as e:
        logger.error(f"Failed to delete memory for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/stats")
async def memory_stats():
    """Get memory statistics."""
    try:
        count = await memory_service.count()
        return {"total_chunks": count}
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        return {"total_chunks": 0, "error": str(e)}
