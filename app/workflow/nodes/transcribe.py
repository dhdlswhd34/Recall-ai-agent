import logging

from app.services.whisper import transcribe_audio
from app.workflow.state import MeetingState

logger = logging.getLogger(__name__)


async def transcribe_node(state: MeetingState) -> dict:
    meeting_id = state["meeting_id"]
    audio_path = state["audio_path"]

    try:
        logger.info(f"[{meeting_id}] Starting transcription")
        transcript = await transcribe_audio(audio_path)
        logger.info(f"[{meeting_id}] Transcription complete ({len(transcript)} chars)")
        return {"transcript": transcript, "transcribe_error": None}
    except Exception as e:
        logger.error(f"[{meeting_id}] Transcription failed: {e}")
        return {
            "transcript": None,
            "transcribe_error": str(e),
            "final_status": "failed",
            "error_message": f"Transcription failed: {e}",
        }
