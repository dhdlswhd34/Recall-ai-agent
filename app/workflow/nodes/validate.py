import logging
import os

from app.config import settings
from app.workflow.state import MeetingState

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "mp4", "webm", "ogg", "flac"}
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


def validate_node(state: MeetingState) -> dict:
    audio_path = state["audio_path"]
    audio_format = state.get("audio_format", "")

    if not os.path.exists(audio_path):
        return {
            "validated": False,
            "validation_error": f"Audio file not found: {audio_path}",
            "final_status": "failed",
            "error_message": f"Audio file not found: {audio_path}",
        }

    ext = audio_format.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        return {
            "validated": False,
            "validation_error": f"Unsupported format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            "final_status": "failed",
            "error_message": f"Unsupported audio format: {ext}",
        }

    file_size = os.path.getsize(audio_path)
    if file_size > MAX_BYTES:
        size_mb = file_size / (1024 * 1024)
        return {
            "validated": False,
            "validation_error": f"File size {size_mb:.1f}MB exceeds {settings.max_upload_size_mb}MB limit",
            "final_status": "failed",
            "error_message": f"File too large: {size_mb:.1f}MB (max {settings.max_upload_size_mb}MB)",
        }

    logger.info(f"Validation passed for meeting {state['meeting_id']}")
    return {"validated": True, "validation_error": None}
