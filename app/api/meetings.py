import asyncio
import json
import logging
import os
import uuid
from typing import List, Optional

import aiosqlite
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.config import settings
from app.database import get_db
from app.models.schemas import MeetingCreateResponse, MeetingListOut, MeetingOut
from app.workflow.graph import run_meeting_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["meetings"])

ALLOWED_CONTENT_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "video/mp4",
    "video/webm",
    "application/octet-stream",
}


def _ext_from_filename(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return parts[-1].lower() if len(parts) == 2 else ""


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=MeetingCreateResponse)
async def create_meeting(
    title: str = Form(...),
    project_id: Optional[str] = Form(None),
    participants: Optional[str] = Form(None),  # JSON array string
    audio: UploadFile = File(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Upload an audio file and start async processing."""
    # Parse participants
    try:
        participants_list = json.loads(participants) if participants else []
        if not isinstance(participants_list, list):
            participants_list = []
    except Exception:
        participants_list = []

    # Determine extension
    filename = audio.filename or "audio"
    ext = _ext_from_filename(filename)
    if not ext:
        ext = "wav"

    # Save file
    meeting_id = str(uuid.uuid4())
    os.makedirs(settings.upload_dir, exist_ok=True)
    audio_path = os.path.join(settings.upload_dir, f"{meeting_id}.{ext}")

    content = await audio.read()

    # Size check (pre-save)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content) / 1024 / 1024:.1f}MB. Max allowed: {settings.max_upload_size_mb}MB",
        )

    with open(audio_path, "wb") as f:
        f.write(content)

    # Insert pending record
    await db.execute(
        """
        INSERT INTO meetings (id, title, project_id, participants, audio_path, audio_format, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
        (
            meeting_id,
            title,
            project_id,
            json.dumps(participants_list, ensure_ascii=False),
            audio_path,
            ext,
        ),
    )
    await db.commit()

    # Fire-and-forget workflow
    asyncio.create_task(
        run_meeting_workflow(
            meeting_id=meeting_id,
            audio_path=audio_path,
            audio_format=ext,
        )
    )

    logger.info(f"Meeting {meeting_id} created, workflow dispatched")
    return MeetingCreateResponse(meeting_id=meeting_id)


@router.get("", response_model=List[MeetingListOut])
async def list_meetings(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List meetings with optional filters."""
    where_clauses = []
    params = []

    if project_id:
        where_clauses.append("project_id = ?")
        params.append(project_id)
    if status:
        where_clauses.append("m.status = ?")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.extend([limit, offset])

    sql = f"""
        SELECT id, title, project_id, status, audio_format, created_at, updated_at
        FROM meetings m
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    async with db.execute(sql, params) as cursor:
        rows = await cursor.fetchall()

    return [
        MeetingListOut(
            id=row["id"],
            title=row["title"],
            project_id=row["project_id"],
            status=row["status"],
            audio_format=row["audio_format"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
    meeting_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get meeting detail including action items, decisions, and issues."""
    async with db.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)) as cursor:
        row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Fetch related data
    async with db.execute(
        "SELECT * FROM action_items WHERE meeting_id = ? ORDER BY created_at",
        (meeting_id,),
    ) as cursor:
        action_rows = await cursor.fetchall()

    async with db.execute(
        "SELECT * FROM decisions WHERE meeting_id = ? ORDER BY created_at",
        (meeting_id,),
    ) as cursor:
        decision_rows = await cursor.fetchall()

    async with db.execute(
        "SELECT * FROM issues WHERE meeting_id = ? ORDER BY created_at",
        (meeting_id,),
    ) as cursor:
        issue_rows = await cursor.fetchall()

    return MeetingOut(
        id=row["id"],
        title=row["title"],
        project_id=row["project_id"],
        participants=row["participants"],
        audio_path=row["audio_path"],
        audio_format=row["audio_format"],
        status=row["status"],
        transcript=row["transcript"],
        summary=row["summary"],
        topics=row["topics"],
        error_message=row["error_message"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        action_items=[
            {
                "id": r["id"],
                "meeting_id": r["meeting_id"],
                "owner": r["owner"],
                "task": r["task"],
                "due_date": r["due_date"],
                "status": r["status"],
                "confidence": r["confidence"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in action_rows
        ],
        decisions=[
            {
                "id": r["id"],
                "meeting_id": r["meeting_id"],
                "decision_text": r["decision_text"],
                "created_at": r["created_at"],
            }
            for r in decision_rows
        ],
        issues=[
            {
                "id": r["id"],
                "meeting_id": r["meeting_id"],
                "issue_text": r["issue_text"],
                "status": r["status"],
                "created_at": r["created_at"],
            }
            for r in issue_rows
        ],
    )
