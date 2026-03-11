import logging

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.schemas import ActionItemOut, ActionItemUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/actions", tags=["actions"])

VALID_STATUSES = {"open", "in_progress", "done"}


@router.patch("/{action_id}", response_model=ActionItemOut)
async def update_action_item(
    action_id: str,
    body: ActionItemUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Update action item status, task description, owner, or due date."""
    async with db.execute("SELECT * FROM action_items WHERE id = ?", (action_id,)) as cursor:
        row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Action item not found")

    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{body.status}'. Must be one of: {', '.join(VALID_STATUSES)}",
        )

    updates = {}
    if body.status is not None:
        updates["status"] = body.status
    if body.task is not None:
        updates["task"] = body.task
    if body.owner is not None:
        updates["owner"] = body.owner
    if body.due_date is not None:
        updates["due_date"] = body.due_date

    if not updates:
        # Nothing to update, return current
        return ActionItemOut(
            id=row["id"],
            meeting_id=row["meeting_id"],
            owner=row["owner"],
            task=row["task"],
            due_date=row["due_date"],
            status=row["status"],
            confidence=row["confidence"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    set_clause += ", updated_at = datetime('now')"
    values = list(updates.values()) + [action_id]

    await db.execute(
        f"UPDATE action_items SET {set_clause} WHERE id = ?",
        values,
    )
    await db.commit()

    async with db.execute("SELECT * FROM action_items WHERE id = ?", (action_id,)) as cursor:
        updated = await cursor.fetchone()

    return ActionItemOut(
        id=updated["id"],
        meeting_id=updated["meeting_id"],
        owner=updated["owner"],
        task=updated["task"],
        due_date=updated["due_date"],
        status=updated["status"],
        confidence=updated["confidence"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )
