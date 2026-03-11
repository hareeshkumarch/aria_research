from .base import get_db

async def create_run(run_id: str, goal: str) -> dict:
    async with get_db() as db:
        await db.execute(
            "INSERT INTO runs (id, goal, status) VALUES (?, ?, 'running')",
            (run_id, goal)
        )
        await db.commit()
    return {"id": run_id, "goal": goal, "status": "running"}

async def update_run(run_id: str, **kwargs):
    async with get_db() as db:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [run_id]
        await db.execute(
            f"UPDATE runs SET {sets}, updated_at = datetime('now') WHERE id = ?",
            vals
        )
        await db.commit()

async def get_run(run_id: str) -> dict | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None

async def list_runs(limit: int = 50, offset: int = 0) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def delete_run(run_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        await db.commit()
