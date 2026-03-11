"""API routes for database explorer — view all tables and data."""
from fastapi import APIRouter, Query
from ..repositories.base import get_db
from ..logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/database/stats")
async def get_database_stats():
    """Get overall database statistics."""
    async with get_db() as db:
        stats = {}
        for table in ["runs", "subtasks", "tool_calls", "run_events", "api_keys"]:
            cursor = await db.execute(f"SELECT COUNT(*) as count FROM {table}")
            row = await cursor.fetchone()
            stats[table] = row["count"] if row else 0

        # Get DB file size
        import os
        from ..repositories.base import DB_PATH
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

        return {
            "tables": stats,
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
        }


@router.get("/database/runs")
async def get_db_runs(limit: int = Query(50, le=200), offset: int = 0):
    """Get all runs from the database."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return {"rows": [dict(r) for r in rows], "table": "runs"}


@router.get("/database/subtasks")
async def get_db_subtasks(
    run_id: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """Get subtasks, optionally filtered by run_id."""
    async with get_db() as db:
        if run_id:
            cursor = await db.execute(
                "SELECT * FROM subtasks WHERE run_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (run_id, limit, offset)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM subtasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        rows = await cursor.fetchall()
        return {"rows": [dict(r) for r in rows], "table": "subtasks"}


@router.get("/database/tool_calls")
async def get_db_tool_calls(
    run_id: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """Get tool calls, optionally filtered by run_id."""
    async with get_db() as db:
        if run_id:
            cursor = await db.execute(
                "SELECT * FROM tool_calls WHERE run_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (run_id, limit, offset)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM tool_calls ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        rows = await cursor.fetchall()
        return {"rows": [dict(r) for r in rows], "table": "tool_calls"}


@router.get("/database/events")
async def get_db_events(
    run_id: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """Get run events, optionally filtered by run_id."""
    async with get_db() as db:
        if run_id:
            cursor = await db.execute(
                "SELECT * FROM run_events WHERE run_id = ? ORDER BY id LIMIT ? OFFSET ?",
                (run_id, limit, offset)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM run_events ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        rows = await cursor.fetchall()
        return {"rows": [dict(r) for r in rows], "table": "run_events"}


@router.delete("/database/table/{table_name}")
async def clear_table(table_name: str):
    """Clear all data from a specific table (dangerous!)."""
    allowed = {"runs", "subtasks", "tool_calls", "run_events"}
    if table_name not in allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Cannot clear table: {table_name}")

    async with get_db() as db:
        # If clearing runs, cascade to related tables
        if table_name == "runs":
            await db.execute("DELETE FROM run_events")
            await db.execute("DELETE FROM tool_calls")
            await db.execute("DELETE FROM subtasks")
            await db.execute("DELETE FROM runs")
        else:
            await db.execute(f"DELETE FROM {table_name}")
        await db.commit()

    return {"message": f"Table '{table_name}' cleared successfully."}
