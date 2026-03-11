import logging

from app.services.llm import call_json_llm
from app.workflow.state import MeetingState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert meeting analyst. Extract action items, decisions, and issues from a meeting transcript.

Respond ONLY with valid JSON in this exact format:
{
  "action_items": [
    {
      "owner": "Person Name or null",
      "task": "Clear description of what needs to be done",
      "due_date": "YYYY-MM-DD or null",
      "confidence": 0.95
    }
  ],
  "decisions": [
    "Decision made during the meeting"
  ],
  "issues": [
    "Problem or blocker identified during the meeting"
  ]
}

Rules:
- action_items: Tasks assigned to people. confidence (0.0-1.0) indicates how clearly the task was assigned.
- decisions: Definitive agreements or choices made
- issues: Problems, blockers, risks mentioned that need attention
- Use null for unknown owner or due_date
- Write in the same language as the transcript"""

USER_TEMPLATE = """Extract action items, decisions, and issues from this meeting transcript:

{transcript}"""


async def extract_node(state: MeetingState) -> dict:
    meeting_id = state["meeting_id"]
    transcript = state.get("transcript", "")

    if not transcript:
        return {
            "action_items": [],
            "decisions": [],
            "issues": [],
            "extract_error": "No transcript available",
        }

    try:
        logger.info(f"[{meeting_id}] Starting extraction")
        result = await call_json_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(transcript=transcript),
        )

        action_items = result.get("action_items", [])
        decisions = result.get("decisions", [])
        issues = result.get("issues", [])

        # Normalize types
        if not isinstance(action_items, list):
            action_items = []
        if not isinstance(decisions, list):
            decisions = []
        if not isinstance(issues, list):
            issues = []

        # Ensure confidence is float
        for item in action_items:
            if isinstance(item, dict):
                item.setdefault("confidence", 1.0)
                item["confidence"] = float(item["confidence"])

        logger.info(
            f"[{meeting_id}] Extracted {len(action_items)} actions, "
            f"{len(decisions)} decisions, {len(issues)} issues"
        )
        return {
            "action_items": action_items,
            "decisions": decisions,
            "issues": issues,
            "extract_error": None,
        }
    except Exception as e:
        logger.error(f"[{meeting_id}] Extraction failed: {e}")
        return {
            "action_items": [],
            "decisions": [],
            "issues": [],
            "extract_error": str(e),
        }
