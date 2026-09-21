"""Persists mlops agent-trace events into the existing `lesson_events` table.

`lesson_events` is already `{event_type, lesson_id, node_id, payload, occurred_at}`
and the orchestrator's `session_id` *is* the lesson id, so agent traces need no
new table — they are lifecycle events with an `agent.` prefix.

The producers (`ai_agent_orchestration`, `rag`) run on executor threads and must
not import the backend, so they emit through the mlops tracer and this sink does
the writing, on its own short-lived session rather than the live WebSocket one.
"""

import logging
from typing import Any, Dict

from modules.backend.src.db.base import SessionLocal
from modules.backend.src.db.models import Lesson, LessonEvent
from modules.mlops.src.agent_trace import tracer

logger = logging.getLogger(__name__)


def _write_event(event: Dict[str, Any]) -> None:
    """Sink callback. Any failure here is logged and swallowed by the tracer."""
    lesson_id = event.get("session_id")
    if not lesson_id:
        return

    db = SessionLocal()
    try:
        # A trace for a session that isn't a persisted lesson (unit tests, a
        # stale session) is dropped rather than violating the foreign key.
        if db.get(Lesson, lesson_id) is None:
            return
        db.add(
            LessonEvent(
                lesson_id=lesson_id,
                event_type=event["event_type"],
                node_id=event.get("node_id"),
                payload=event.get("payload") or {},
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not persist agent trace event %s", event.get("event_type"))
    finally:
        db.close()


def install() -> None:
    """Point the process-wide tracer at this sink. Called once at startup."""
    tracer.set_sink(_write_event)
    logger.info("Agent trace sink installed (events -> lesson_events)")
