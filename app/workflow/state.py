from __future__ import annotations

from typing import Any, List, Optional, TypedDict


class ActionItemData(TypedDict):
    owner: Optional[str]
    task: str
    due_date: Optional[str]
    confidence: float


class MeetingState(TypedDict):
    meeting_id: str
    audio_path: str
    audio_format: str

    # Validation
    validated: bool
    validation_error: Optional[str]

    # Transcription
    transcript: Optional[str]
    transcribe_error: Optional[str]

    # Summarization
    summary: Optional[str]
    topics: List[str]
    summarize_error: Optional[str]

    # Extraction
    action_items: List[ActionItemData]
    decisions: List[str]
    issues: List[str]
    extract_error: Optional[str]

    # Embedding
    embedding: Optional[List[float]]
    embed_error: Optional[str]

    # Final
    final_status: str  # done | failed
    error_message: Optional[str]

    # Google Docs export
    docs_url: Optional[str]
    docs_error: Optional[str]
