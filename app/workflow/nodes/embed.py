import logging

from app.services.llm import get_embedding
from app.workflow.state import MeetingState

logger = logging.getLogger(__name__)


async def embed_node(state: MeetingState) -> dict:
    meeting_id = state["meeting_id"]
    summary = state.get("summary", "") or ""
    topics = state.get("topics", []) or []

    if not summary and not topics:
        logger.warning(f"[{meeting_id}] No content to embed")
        return {"embedding": None, "embed_error": "No content to embed"}

    try:
        text = summary
        if topics:
            text += "\nTopics: " + ", ".join(topics)

        logger.info(f"[{meeting_id}] Generating embedding")
        embedding = await get_embedding(text)
        logger.info(f"[{meeting_id}] Embedding generated ({len(embedding)} dims)")
        return {"embedding": embedding, "embed_error": None}
    except Exception as e:
        logger.error(f"[{meeting_id}] Embedding failed: {e}")
        return {"embedding": None, "embed_error": str(e)}
