import json
import logging
import uuid
from typing import Optional

import aiosqlite

from app.config import settings
from app.database import is_vec_loaded
from app.workflow.state import MeetingState

logger = logging.getLogger(__name__)


async def persist_node(state: MeetingState) -> dict:
    meeting_id = state["meeting_id"]
    final_status = state.get("final_status", "done")

    # Determine overall status
    if final_status != "failed":
        final_status = "done"

    error_message = state.get("error_message")
    transcript = state.get("transcript")
    summary = state.get("summary")
    topics = state.get("topics", [])
    action_items = state.get("action_items", [])
    decisions = state.get("decisions", [])
    issues = state.get("issues", [])
    embedding = state.get("embedding")

    try:
        async with aiosqlite.connect(settings.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")

            # Update meetings row
            await db.execute(
                """
                UPDATE meetings
                SET status = ?, transcript = ?, summary = ?, topics = ?,
                    error_message = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    final_status,
                    transcript,
                    summary,
                    json.dumps(topics or [], ensure_ascii=False),
                    error_message,
                    meeting_id,
                ),
            )

            # Insert action items
            for item in action_items:
                if not isinstance(item, dict) or not item.get("task"):
                    continue
                await db.execute(
                    """
                    INSERT INTO action_items (id, meeting_id, owner, task, due_date, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        meeting_id,
                        item.get("owner"),
                        item["task"],
                        item.get("due_date"),
                        float(item.get("confidence", 1.0)),
                    ),
                )

            # Insert decisions
            for decision_text in decisions:
                if not isinstance(decision_text, str) or not decision_text.strip():
                    continue
                await db.execute(
                    "INSERT INTO decisions (id, meeting_id, decision_text) VALUES (?, ?, ?)",
                    (str(uuid.uuid4()), meeting_id, decision_text.strip()),
                )

            # Insert issues
            for issue_text in issues:
                if not isinstance(issue_text, str) or not issue_text.strip():
                    continue
                await db.execute(
                    "INSERT INTO issues (id, meeting_id, issue_text) VALUES (?, ?, ?)",
                    (str(uuid.uuid4()), meeting_id, issue_text.strip()),
                )

            # Insert embedding if available
            if embedding and is_vec_loaded():
                try:
                    await db.enable_load_extension(True)
                    import sqlite_vec
                    sqlite_vec.load(db)
                    await db.enable_load_extension(False)
                    embedding_bytes = sqlite_vec.serialize_float32(embedding)
                    await db.execute(
                        "INSERT OR REPLACE INTO meeting_embeddings (meeting_id, embedding) VALUES (?, ?)",
                        (meeting_id, embedding_bytes),
                    )
                except Exception as e:
                    logger.warning(f"[{meeting_id}] Failed to store embedding: {e}")

            await db.commit()

        logger.info(f"[{meeting_id}] Persisted with status={final_status}")
    except Exception as e:
        logger.error(f"[{meeting_id}] Persist failed: {e}")
        # Try to mark as failed
        try:
            async with aiosqlite.connect(settings.db_path) as db:
                await db.execute(
                    "UPDATE meetings SET status='failed', error_message=?, updated_at=datetime('now') WHERE id=?",
                    (f"Persist error: {e}", meeting_id),
                )
                await db.commit()
        except Exception as inner:
            logger.error(f"[{meeting_id}] Could not update status to failed: {inner}")

    return {}
