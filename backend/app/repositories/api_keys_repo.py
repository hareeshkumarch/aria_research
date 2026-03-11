from .base import get_db

async def get_all_api_keys() -> dict[str, str]:
    async with get_db() as db:
        cursor = await db.execute("SELECT provider_id, api_key FROM api_keys")
        rows = await cursor.fetchall()
        return {r["provider_id"]: r["api_key"] for r in rows}

async def save_api_key(provider_id: str, api_key: str):
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO api_keys (provider_id, api_key, updated_at) VALUES (?, ?, datetime('now'))",
            (provider_id, api_key)
        )
        await db.commit()

async def delete_api_key(provider_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM api_keys WHERE provider_id = ?", (provider_id,))
        await db.commit()
