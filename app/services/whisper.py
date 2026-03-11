import logging
from pathlib import Path

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def transcribe_audio(audio_path: str) -> str:
    """
    Call Whisper API and return transcript in [MM:SS] text format.
    """
    client = get_client()
    path = Path(audio_path)

    with open(path, "rb") as audio_file:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = getattr(response, "segments", None) or []
    if segments:
        lines = []
        for seg in segments:
            start = seg.get("start", 0) if isinstance(seg, dict) else getattr(seg, "start", 0)
            text = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
            minutes = int(start) // 60
            seconds = int(start) % 60
            lines.append(f"[{minutes:02d}:{seconds:02d}] {text.strip()}")
        return "\n".join(lines)

    # Fallback: no segments, return plain text
    text = getattr(response, "text", "") or ""
    return text
