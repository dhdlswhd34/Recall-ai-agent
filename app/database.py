import logging
import os
import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meetings (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    project_id    TEXT,
    participants  TEXT NOT NULL DEFAULT '[]',
    audio_path    TEXT NOT NULL,
    audio_format  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    transcript    TEXT,
    summary       TEXT,
    topics        TEXT,
    error_message TEXT,
    docs_url      TEXT,
    created_at    DATETIME DEFAULT (datetime('now')),
    updated_at    DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS action_items (
    id         TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    owner      TEXT,
    task       TEXT NOT NULL,
    due_date   TEXT,
    status     TEXT NOT NULL DEFAULT 'open',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS decisions (
    id            TEXT PRIMARY KEY,
    meeting_id    TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    decision_text TEXT NOT NULL,
    created_at    DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS issues (
    id         TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    issue_text TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'open',
    created_at DATETIME DEFAULT (datetime('now'))
);
"""

VECTOR_TABLE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS meeting_embeddings USING vec0(
    meeting_id TEXT,
    embedding  FLOAT[1536]
);
"""

_vec_loaded = False


async def init_db() -> None:
    global _vec_loaded
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)

    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(SCHEMA_SQL)

        # Migrate: add docs_url column if missing (existing DBs)
        try:
            await db.execute("ALTER TABLE meetings ADD COLUMN docs_url TEXT")
            await db.commit()
            logger.info("Migrated: added docs_url column")
        except Exception:
            pass  # Column already exists

        # Try loading sqlite-vec extension
        try:
            import sqlite_vec
            db.row_factory = aiosqlite.Row
            await db.enable_load_extension(True)
            sqlite_vec.load(db)
            await db.enable_load_extension(False)
            await db.executescript(VECTOR_TABLE_SQL)
            _vec_loaded = True
            logger.info("sqlite-vec loaded successfully")
        except Exception as e:
            logger.warning(f"sqlite-vec not available, vector search disabled: {e}")
            _vec_loaded = False

        await db.commit()


def is_vec_loaded() -> bool:
    return _vec_loaded


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.db_path)
    db.row_factory = aiosqlite.Row
    try:
        if _vec_loaded:
            try:
                import sqlite_vec
                await db.enable_load_extension(True)
                sqlite_vec.load(db)
                await db.enable_load_extension(False)
            except Exception:
                pass
        yield db
    finally:
        await db.close()
