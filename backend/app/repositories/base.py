"""Async SQLite database for persistent storage."""
import os
import aiosqlite
from contextlib import asynccontextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aria.db")

async def init_db():
    """Create tables if they don't exist and tune SQLite for better throughput."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Lightweight pragmas to improve write performance without sacrificing correctness
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.execute("PRAGMA cache_size=-64000;")  # ~64MB page cache

        await db.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                final_output TEXT,
                critic_score REAL,
                error_detail TEXT
            );

            CREATE TABLE IF NOT EXISTS subtasks (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT,
                query TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                tool_hint TEXT,
                dependencies TEXT DEFAULT '[]',
                result TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                retry_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tool_calls (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                subtask_id TEXT,
                tool_name TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                success INTEGER NOT NULL DEFAULT 1,
                duration_ms INTEGER,
                tokens_used INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                node TEXT,
                payload TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                provider_id TEXT PRIMARY KEY,
                api_key TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_subtasks_run_id ON subtasks(run_id);
            CREATE INDEX IF NOT EXISTS idx_tool_calls_run_id ON tool_calls(run_id);
            CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id);
        """)
        await db.commit()

        # Lightweight migrations for existing DBs (add columns if missing)
        cursor = await db.execute("PRAGMA table_info(runs)")
        cols = {row[1] for row in await cursor.fetchall()}
        if "input_tokens" not in cols:
            await db.execute("ALTER TABLE runs ADD COLUMN input_tokens INTEGER DEFAULT 0")
        if "output_tokens" not in cols:
            await db.execute("ALTER TABLE runs ADD COLUMN output_tokens INTEGER DEFAULT 0")
        await db.commit()

@asynccontextmanager
async def get_db():
    """Async context manager for database connections."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    # Apply the same pragmatic tuning on all connections
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    try:
        yield db
    finally:
        await db.close()
