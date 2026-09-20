"""Bridges persisted Lesson rows to the orchestrator's in-memory SessionState.

The orchestrator keeps session state in process memory. On its own that means a
restart, or a second worker, loses a lesson mid-flight. This manager rebuilds
that state from the database whenever it is missing, so a learner can close the
tab and resume the same lesson later.
"""
import logging
import threading
from typing import Any, Optional

from modules.ai_agent_orchestration.src.schemas.lesson import (
    LearnerConstraints,
    LessonNode,
    LessonPlan,
)
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.backend.src.db.models import Lesson

logger = logging.getLogger(__name__)

# FSM states a lesson can legitimately resume from.
_RESUMABLE = {
    "EXPLAIN": TeacherState.EXPLAIN,
    "DEMONSTRATE": TeacherState.EXPLAIN,  # re-render rather than await a lost job
    "QUESTION": TeacherState.EXPLAIN,     # re-teach so the question has context
    "EVALUATE": TeacherState.EXPLAIN,
    "ADAPT": TeacherState.EXPLAIN,
    "CONTINUE": TeacherState.CONTINUE,
    "PLAN": TeacherState.PLAN,
}


class SessionManager:
    """Thread-safe access to orchestrator sessions keyed by lesson id."""

    def __init__(self):
        self._lock = threading.RLock()

    @property
    def _ai(self):
        from modules.backend.src.integrations.container import services

        return services["ai_service"]

    # -- construction --------------------------------------------------------

    @staticmethod
    def constraints_for(lesson: Lesson) -> LearnerConstraints:
        return LearnerConstraints(
            level=lesson.level,
            language=lesson.language,
            time_budget_min=lesson.time_budget_min,
            style=lesson.style,
        )

    def _fresh_session(self, lesson: Lesson, document_outline: Optional[dict] = None):
        session = self._ai.init_session(lesson.id)
        session.constraints = self.constraints_for(lesson)
        session.topic = lesson.topic
        session.document_id = lesson.document_id
        session.document_outline = document_outline
        return session

    @staticmethod
    def outline_for(lesson: Lesson, db=None) -> Optional[dict]:
        """What the lesson's source document is about, for the planner.

        Uses the chapters and key terms recorded at ingest time, so a
        document-sourced lesson is planned from the document rather than from an
        invented topic.
        """
        if not lesson.document_id:
            return None

        document = getattr(lesson, "document", None)
        if document is None and db is not None:
            from modules.backend.src.db.models import Document

            document = db.get(Document, lesson.document_id)
        if document is None:
            logger.warning(
                "Lesson %s references document %s, which could not be loaded",
                lesson.id,
                lesson.document_id,
            )
            return None

        outline = {
            "document_id": document.id,
            "filename": document.filename,
            "language": document.source_lang,
            "chapters": list(document.chapters or [])[:12],
            "key_terms": list(document.key_terms or [])[:24],
        }

        # Headings alone can be uninformative, so include a few real passages.
        try:
            from modules.backend.src.integrations.container import services

            rag = services["rag_service"]
            query = " ".join(outline["chapters"][:3]) or document.filename
            result = rag.retrieve_context(document_id=document.id, query_text=query, top_k=4)
            outline["excerpts"] = [c.text[:700] for c in result.chunks][:4]
        except Exception:
            logger.warning("Could not fetch excerpts for document %s", document.id, exc_info=True)
            outline["excerpts"] = []

        return outline

    def _rehydrate_plan(self, session, lesson: Lesson) -> None:
        """Rebuild the LessonPlan from plan_json written at planning time."""
        if not lesson.plan_json:
            return
        try:
            raw = dict(lesson.plan_json)
            nodes = [LessonNode(**n) for n in raw.get("nodes", [])]
            session.lesson_plan = LessonPlan(
                lesson_id=raw.get("lesson_id") or lesson.id,
                source=raw.get("source") or lesson.source,
                constraints=self.constraints_for(lesson),
                nodes=nodes,
            )
            session.current_node_index = min(
                max(lesson.current_node_index, 0), max(len(nodes) - 1, 0)
            )
        except Exception:
            logger.exception("Could not rehydrate plan for lesson %s", lesson.id)

    def get_or_restore(self, lesson: Lesson, db=None):
        """Return a live SessionState for this lesson, rebuilding it if needed."""
        with self._lock:
            try:
                session = self._ai.get_session(lesson.id)
            except KeyError:
                session = self._fresh_session(lesson, self.outline_for(lesson, db))
                self._rehydrate_plan(session, lesson)
                logger.info("Restored orchestrator session for lesson %s", lesson.id)
                return session

            # An existing session may predate the plan (e.g. after a re-plan).
            if lesson.plan_json and not session.lesson_plan:
                self._rehydrate_plan(session, lesson)
            if session.constraints is None:
                session.constraints = self.constraints_for(lesson)
            return session

    def reset(self, lesson_id: str) -> None:
        with self._lock:
            self._ai.sessions.pop(lesson_id, None)

    # -- FSM driving ---------------------------------------------------------

    def build_plan(self, lesson: Lesson, db=None) -> Any:
        """Run UNDERSTAND then PLAN, returning the generated LessonPlan."""
        outline = self.outline_for(lesson, db)
        with self._lock:
            self.reset(lesson.id)
            self._fresh_session(lesson, outline)
            state, _ = self.step(
                lesson,
                TeacherState.UNDERSTAND,
                {
                    "constraints": self.constraints_for(lesson),
                    "topic": lesson.topic,
                    "document_id": lesson.document_id,
                    "document_outline": outline,
                },
            )
            _, plan = self.step(lesson, state, {})
            return plan

    def current_grounding(self, lesson: Lesson) -> list:
        """Passages that grounded the most recent explanation, for citation."""
        session = self.get_or_restore(lesson)
        return list(getattr(session, "recent_grounding", []) or [])

    def current_provenance(self, lesson: Lesson) -> dict:
        """Where the most recent explanation came from, and how well grounded."""
        session = self.get_or_restore(lesson)
        return {
            "chunks": list(getattr(session, "recent_provenance", []) or []),
            "risk_level": getattr(session, "recent_risk_level", "low"),
        }

    def step(self, lesson: Lesson, state: TeacherState, inputs: dict):
        self.get_or_restore(lesson)
        return self._ai.process_next_step(lesson.id, state, inputs)

    def resume_state(self, lesson: Lesson) -> TeacherState:
        """Decide which FSM state a reconnecting learner should re-enter."""
        if lesson.status == "completed":
            return TeacherState.DONE
        if not lesson.plan_json:
            return TeacherState.PLAN
        return _RESUMABLE.get(lesson.fsm_state, TeacherState.EXPLAIN)

    def current_node(self, lesson: Lesson) -> Optional[Any]:
        session = self.get_or_restore(lesson)
        plan = session.lesson_plan
        if not plan or not plan.nodes:
            return None
        index = min(session.current_node_index, len(plan.nodes) - 1)
        return plan.nodes[index]

    def sync_index(self, lesson: Lesson) -> int:
        session = self.get_or_restore(lesson)
        return session.current_node_index


session_manager = SessionManager()
