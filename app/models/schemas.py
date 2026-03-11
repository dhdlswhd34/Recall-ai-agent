from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    project_id: Optional[str] = None
    participants: List[str] = Field(default_factory=list)


class ActionItemOut(BaseModel):
    id: str
    meeting_id: str
    owner: Optional[str] = None
    task: str
    due_date: Optional[str] = None
    status: str
    confidence: float
    created_at: str
    updated_at: str


class DecisionOut(BaseModel):
    id: str
    meeting_id: str
    decision_text: str
    created_at: str


class IssueOut(BaseModel):
    id: str
    meeting_id: str
    issue_text: str
    status: str
    created_at: str


class MeetingOut(BaseModel):
    id: str
    title: str
    project_id: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    audio_path: str
    audio_format: str
    status: str
    transcript: Optional[str] = None
    summary: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    action_items: List[ActionItemOut] = Field(default_factory=list)
    decisions: List[DecisionOut] = Field(default_factory=list)
    issues: List[IssueOut] = Field(default_factory=list)

    @field_validator("participants", "topics", mode="before")
    @classmethod
    def parse_json_list(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        if v is None:
            return []
        return v


class MeetingListOut(BaseModel):
    id: str
    title: str
    project_id: Optional[str] = None
    status: str
    audio_format: str
    created_at: str
    updated_at: str


class MeetingCreateResponse(BaseModel):
    meeting_id: str
    status: str = "pending"
    message: str = "Meeting uploaded successfully. Processing has started."


class ActionItemUpdate(BaseModel):
    status: Optional[str] = None
    task: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
