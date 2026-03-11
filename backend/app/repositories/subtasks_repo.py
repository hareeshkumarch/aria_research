import json
from .base import get_db

async def save_subtasks(run_id: str, subtasks: list[dict]):
    async with get_db() as db:
        for st in subtasks:
            await db.execute(
                """INSERT OR REPLACE INTO subtasks
                   (id, run_id, title, description, query, status, tool_hint, dependencies)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"{run_id}_{st.get('id', '')}",
                    run_id,
                    st.get("title", ""),
                    st.get("description", ""),
                    st.get("query", ""),
                    st.get("status", "pending"),
                    st.get("tool_hint", "web_search"),
                    json.dumps(st.get("dependencies", [])),
                )
            )
        await db.commit()
