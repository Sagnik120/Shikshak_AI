"""Structured agent-decision tracing.

`rag/src/perf.py` already measures *how long* each pipeline stage took. This
records *what the agent decided and why*: which chunks grounded a node, whether
retrieval had to be refined, which adaptation branch was taken. Without it the
agentic behaviour added around the FSM is neither demonstrable nor debuggable.

Design constraints:

* **Observable metadata only.** Prompts, scripts and raw LLM output are never
  recorded — `_SENSITIVE_KEYS` drops them even if a caller passes them by
  mistake, so a trace can be shown to a learner or a judge safely.
* **No module may import the backend to emit an event.** Producers
  (`ai_agent_orchestration`, `rag`) call `tracer.emit(...)`; the backend installs
  a sink that persists them. mlops itself depends on nothing.
* **Tracing must never break teaching.** Every failure path here is swallowed
  and logged; a broken sink degrades to log-only.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Payload keys that could carry prompt text, chain-of-thought or PII. Dropped
# before an event is stored, regardless of who emitted it.
_SENSITIVE_KEYS = frozenset(
    {
        "prompt", "system_prompt", "user_prompt", "messages", "script_text",
        "raw_answer", "raw_output", "llm_output", "response_text", "text",
        "email", "password", "api_key", "token", "reasoning", "chain_of_thought",
    }
)

# A single value is metadata, not content. Anything longer is almost certainly
# prose that does not belong in a trace.
_MAX_VALUE_CHARS = 300

# Event types, so producers and the UI agree on one vocabulary.
PLAN_GENERATED = "agent.plan_generated"
RETRIEVAL_ATTEMPT = "agent.retrieval_attempt"
RETRIEVAL_RESOLVED = "agent.retrieval_resolved"
SEGMENT_GENERATED = "agent.segment_generated"
QUESTION_GENERATED = "agent.question_generated"
ANSWER_EVALUATED = "agent.answer_evaluated"
ADAPTATION_DECIDED = "agent.adaptation_decided"
MEMORY_READ = "agent.memory_read"


def _scrub(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Keep observable metadata; drop anything that looks like content."""
    clean: Dict[str, Any] = {}
    for key, value in (payload or {}).items():
        if key.lower() in _SENSITIVE_KEYS:
            continue
        if isinstance(value, str) and len(value) > _MAX_VALUE_CHARS:
            value = value[:_MAX_VALUE_CHARS] + "…"
        if isinstance(value, (str, int, float, bool, type(None), list, dict)):
            clean[key] = value
    return clean


class AgentTracer:
    """Collects agent-decision events and hands them to an installed sink."""

    def __init__(self) -> None:
        self._sink: Optional[Callable[[Dict[str, Any]], None]] = None
        self._enabled = True

    def set_sink(self, sink: Optional[Callable[[Dict[str, Any]], None]]) -> None:
        """Install the persistence callback (the backend does this at startup)."""
        self._sink = sink

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def emit(
        self,
        event_type: str,
        session_id: Optional[str],
        node_id: Optional[str] = None,
        **payload: Any,
    ) -> Dict[str, Any]:
        """Record one decision. Returns the event; never raises."""
        event = {
            "event_type": event_type,
            "session_id": session_id or "",
            "node_id": node_id,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": _scrub(payload),
        }

        if not self._enabled:
            return event

        logger.info("AgentTrace %s %s", event_type, event["payload"])

        if self._sink and session_id:
            try:
                self._sink(event)
            except Exception:
                # A failed trace write must never interrupt a lesson.
                logger.exception("Agent trace sink failed for %s", event_type)
        return event


tracer = AgentTracer()
