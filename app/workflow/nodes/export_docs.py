import json
import logging

import aiosqlite

from app.config import settings
from app.workflow.state import MeetingState

logger = logging.getLogger(__name__)


async def export_docs_node(state: MeetingState) -> dict:
    meeting_id = state["meeting_id"]

    if not settings.gws_enabled:
        return {"docs_url": None, "docs_error": None}

    if state.get("final_status") == "failed":
        logger.info(f"[{meeting_id}] Skipping Docs export: meeting processing failed")
        return {"docs_url": None, "docs_error": "Skipped: meeting processing failed"}

    summary = state.get("summary")
    if not summary:
        return {"docs_url": None, "docs_error": "Skipped: no summary available"}

    try:
        # Load persisted data from DB (action_items/decisions/issues already written by persist_node)
        async with aiosqlite.connect(settings.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)) as cursor:
                row = await cursor.fetchone()

            async with db.execute(
                "SELECT owner, task, due_date FROM action_items WHERE meeting_id = ?",
                (meeting_id,),
            ) as cursor:
                action_rows = await cursor.fetchall()

            async with db.execute(
                "SELECT decision_text FROM decisions WHERE meeting_id = ?",
                (meeting_id,),
            ) as cursor:
                decision_rows = await cursor.fetchall()

            async with db.execute(
                "SELECT issue_text FROM issues WHERE meeting_id = ?",
                (meeting_id,),
            ) as cursor:
                issue_rows = await cursor.fetchall()

        participants = json.loads(row["participants"] or "[]")
        action_items = [dict(r) for r in action_rows]
        decisions = [r["decision_text"] for r in decision_rows]
        issues = [r["issue_text"] for r in issue_rows]

        from app.services.google_docs import create_meeting_doc

        logger.info(f"[{meeting_id}] Creating Google Doc")
        docs_url = await create_meeting_doc(
            title=row["title"],
            created_at=row["created_at"],
            participants=participants,
            project_id=row["project_id"],
            summary=summary,
            topics=state.get("topics", []),
            action_items=action_items,
            decisions=decisions,
            issues=issues,
            folder_id=settings.gws_folder_id,
        )

        # Save docs_url back to DB
        async with aiosqlite.connect(settings.db_path) as db:
            await db.execute(
                "UPDATE meetings SET docs_url = ?, updated_at = datetime('now') WHERE id = ?",
                (docs_url, meeting_id),
            )
            await db.commit()

        logger.info(f"[{meeting_id}] Google Doc created: {docs_url}")
        return {"docs_url": docs_url, "docs_error": None}

    except Exception as e:
        logger.error(f"[{meeting_id}] Google Docs export failed: {e}")
        return {"docs_url": None, "docs_error": str(e)}
