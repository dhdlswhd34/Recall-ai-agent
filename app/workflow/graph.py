import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from app.workflow.nodes.embed import embed_node
from app.workflow.nodes.extract import extract_node
from app.workflow.nodes.persist import persist_node
from app.workflow.nodes.summarize import summarize_node
from app.workflow.nodes.transcribe import transcribe_node
from app.workflow.nodes.validate import validate_node
from app.workflow.state import MeetingState

logger = logging.getLogger(__name__)


def route_after_validate(state: MeetingState) -> Literal["transcribe", "persist"]:
    if state.get("validated"):
        return "transcribe"
    return "persist"


def route_after_transcribe(state: MeetingState) -> Literal["summarize", "persist"]:
    if state.get("transcript") and not state.get("transcribe_error"):
        return "summarize"
    return "persist"


def route_after_summarize(state: MeetingState) -> Literal["extract", "persist"]:
    if state.get("summary") and not state.get("summarize_error"):
        return "extract"
    return "persist"


def route_after_extract(state: MeetingState) -> Literal["embed", "persist"]:
    # Extraction is best-effort; always continue to embed if we have summary
    if state.get("summary"):
        return "embed"
    return "persist"


def build_graph() -> StateGraph:
    builder = StateGraph(MeetingState)

    builder.add_node("validate", validate_node)
    builder.add_node("transcribe", transcribe_node)
    builder.add_node("summarize", summarize_node)
    builder.add_node("extract", extract_node)
    builder.add_node("embed", embed_node)
    builder.add_node("persist", persist_node)

    builder.set_entry_point("validate")

    builder.add_conditional_edges("validate", route_after_validate)
    builder.add_conditional_edges("transcribe", route_after_transcribe)
    builder.add_conditional_edges("summarize", route_after_summarize)
    builder.add_conditional_edges("extract", route_after_extract)

    builder.add_edge("embed", "persist")
    builder.add_edge("persist", END)

    return builder.compile()


# Compile once at module load
graph = build_graph()


async def run_meeting_workflow(
    meeting_id: str,
    audio_path: str,
    audio_format: str,
) -> None:
    initial_state: MeetingState = {
        "meeting_id": meeting_id,
        "audio_path": audio_path,
        "audio_format": audio_format,
        "validated": False,
        "validation_error": None,
        "transcript": None,
        "transcribe_error": None,
        "summary": None,
        "topics": [],
        "summarize_error": None,
        "action_items": [],
        "decisions": [],
        "issues": [],
        "extract_error": None,
        "embedding": None,
        "embed_error": None,
        "final_status": "done",
        "error_message": None,
    }

    try:
        logger.info(f"[{meeting_id}] Workflow started")
        await graph.ainvoke(initial_state)
        logger.info(f"[{meeting_id}] Workflow finished")
    except Exception as e:
        logger.error(f"[{meeting_id}] Workflow crashed: {e}", exc_info=True)
        # persist_node handles failure recording, but if graph itself crashes:
        import aiosqlite
        from app.config import settings
        try:
            async with aiosqlite.connect(settings.db_path) as db:
                await db.execute(
                    "UPDATE meetings SET status='failed', error_message=?, updated_at=datetime('now') WHERE id=?",
                    (f"Workflow error: {e}", meeting_id),
                )
                await db.commit()
        except Exception as inner:
            logger.error(f"[{meeting_id}] Could not record crash: {inner}")
