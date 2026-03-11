import logging

from app.services.llm import call_json_llm
from app.workflow.state import MeetingState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert meeting analyst. Given a meeting transcript, produce a concise summary and extract key topics.

Respond ONLY with valid JSON in this exact format:
{
  "summary": "A clear, concise summary of the meeting (2-5 sentences)",
  "topics": ["topic1", "topic2", "topic3"]
}

Rules:
- summary: Capture the main purpose, key discussions, and outcomes
- topics: 3-7 short topic labels (e.g., "Q3 Budget Review", "Product Roadmap")
- Write in the same language as the transcript"""

USER_TEMPLATE = """Please summarize this meeting transcript:

{transcript}"""


async def summarize_node(state: MeetingState) -> dict:
    meeting_id = state["meeting_id"]
    transcript = state.get("transcript", "")

    if not transcript:
        return {
            "summary": None,
            "topics": [],
            "summarize_error": "No transcript available",
            "final_status": "failed",
            "error_message": "Cannot summarize: transcript is empty",
        }

    try:
        logger.info(f"[{meeting_id}] Starting summarization")
        result = await call_json_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(transcript=transcript),
        )

        summary = result.get("summary", "")
        topics = result.get("topics", [])

        if not isinstance(topics, list):
            topics = []

        logger.info(f"[{meeting_id}] Summarization complete, {len(topics)} topics")
        return {"summary": summary, "topics": topics, "summarize_error": None}
    except Exception as e:
        logger.error(f"[{meeting_id}] Summarization failed: {e}")
        return {
            "summary": None,
            "topics": [],
            "summarize_error": str(e),
            "final_status": "failed",
            "error_message": f"Summarization failed: {e}",
        }
