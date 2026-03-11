import uuid
from .base import get_db

async def save_tool_call(run_id: str, subtask_id: str, tool_name: str,
                         input_data: str, output_data: str, success: bool,
                         duration_ms: int, tokens_used: int = 0):
    async with get_db() as db:
        await db.execute(
            """INSERT INTO tool_calls
               (id, run_id, subtask_id, tool_name, input_data, output_data,
                success, duration_ms, tokens_used)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), run_id, subtask_id, tool_name,
             input_data, output_data, 1 if success else 0, duration_ms, tokens_used)
        )
        await db.commit()

async def save_run_event(run_id: str, event_type: str, node: str, payload: str):
    async with get_db() as db:
        await db.execute(
            "INSERT INTO run_events (run_id, event_type, node, payload) VALUES (?, ?, ?, ?)",
            (run_id, event_type, node, payload)
        )
        await db.commit()

async def get_run_events(run_id: str) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM run_events WHERE run_id = ? ORDER BY id",
            (run_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
