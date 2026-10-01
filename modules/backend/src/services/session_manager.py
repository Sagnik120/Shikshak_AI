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
        # (lesson_id, node_id) -> (render job id, script it renders). A learner
        # who reconnects mid-render waits on the SAME job instead of paying for
        # a second LLM call and render of a different script.
        self._render_jobs: dict[tuple[str, str], tuple[str, str]] = {}

    # -- reconnect support ---------------------------------------------------

    def remember_render(self, lesson_id: str, node_id: str, job_id: str, script: str) -> None:
        with self._lock:
            self._render_jobs[(lesson_id, node_id)] = (job_id, script)

    def render_job_for(self, lesson_id: str, node_id: str, script: str) -> Optional[str]:
        with self._lock:
            entry = self._render_jobs.get((lesson_id, node_id))
        return entry[0] if entry and entry[1] == script else None

    def restore_segment(self, lesson: Lesson, row) -> Any:
        """Put the persisted explanation back as the session's recent segment,
        so the question and grading use the script the learner actually saw."""
        from modules.ai_agent_orchestration.src.schemas.teaching import TeachingSegment

        visual = row.visual_json or {"type": row.visual_type or "diagram", "content": row.concept}
        segment = TeachingSegment(
            node_id=row.node_id,
            script_text=row.script_text or "",
            language=lesson.language or "en",
            visual_spec=visual,
            avatar_cue="neutral",
            notes=row.notes_json or None,
        )
        self.get_or_restore(lesson).recent_segment = segment
        return segment

    def checkpoint_questions(self, lesson: Lesson, node: Any, segment: Any) -> list:
        """Mid-video questions for this segment: [(word_offset, InteractionEvent)]."""
        orchestrator = self._ai.orchestrator
        positions = orchestrator.checkpoint_positions(getattr(segment, "script_text", "") or "")
        if not positions:
            return []
        questions = orchestrator.generate_checkpoints(lesson.id, node, segment, positions)
        return list(zip(positions, questions))

    @staticmethod
    def _history_from_db(lesson: Lesson) -> list:
        """Graded answers so far, so lesson-wide escalation survives a restart."""
        from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult

        # Wrong answers before a "continue" or "learn again" no longer count.
        reset = lesson.history_reset_at
        graded = sorted(
            (i for i in lesson.interactions
             if i.correct is not None and (reset is None or i.asked_at >= reset)),
            key=lambda i: i.asked_at,
        )
        return [
            EvaluationResult(
                node_id=i.node_id,
                correct=bool(i.correct),
                partial_credit=float(i.partial_credit or 0.0),
                misconception_tag=i.misconception_tag,
                confidence=min(1.0, max(0.0, float(i.confidence or 0.0))),
                feedback_text=i.feedback_text or "",
            )
            for i in graded
        ]

    def reload_history(self, lesson: Lesson) -> None:
        """Re-read the answer history (e.g. once a fresh-count window ends)."""
        self.get_or_restore(lesson).evaluation_history = self._history_from_db(lesson)

    def restore_question(self, lesson: Lesson, interaction) -> None:
        """Re-arm grading for a question asked before the connection dropped."""
        from modules.ai_agent_orchestration.src.schemas.interaction import InteractionEvent

        self.get_or_restore(lesson).recent_question = InteractionEvent(
            node_id=interaction.node_id,
            question_text=interaction.question_text,
            type=interaction.question_type,
            options=list(interaction.options or []),
            expected_concept=interaction.expected_concept or "",
        )

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

    def _fresh_session(self, lesson: Lesson, document_outline: Optional[dict] = None, db=None):
        session = self._ai.init_session(lesson.id)
        session.constraints = self.constraints_for(lesson)
        session.topic = lesson.topic
        session.document_id = lesson.document_id
        session.document_outline = document_outline
        session.learner_profile = self.memory_for(lesson, db)
        return session

    @staticmethod
    def memory_for(lesson: Lesson, db=None) -> Optional[dict]:
        """What previous lessons established about this learner, for planning only.

        Deliberately narrow: mastered/weak concepts and recurring misconception
        tags, reusing the vocabulary ml_core already produces. No transcripts, no
        raw answers, no identifiers — only what can bias the next lesson plan.
        Returns None for a learner with no history, so a first lesson plans
        exactly as it did before.
        """
        if db is None:
            return None

        from modules.backend.src.db.models import LearnerProfileRow

        profile = db.get(LearnerProfileRow, lesson.user_id)
        if profile is None:
            return None

        # Only tags seen more than once are "recurring" — a single slip should
        # not bias every future lesson.
        recurring = sorted(
            (tag for tag, count in (profile.misconception_counts or {}).items() if count > 1),
            key=lambda tag: profile.misconception_counts[tag],
            reverse=True,
        )[:5]

        memory = {
            "strong_concepts": list(profile.strong_concepts or [])[:8],
            "weak_concepts": list(profile.weak_concepts or [])[:8],
            "recurring_misconceptions": recurring,
            "lessons_completed": profile.lessons_completed,
        }

        # Nothing learned yet: treat as no memory rather than sending empty lists.
        if not any([memory["strong_concepts"], memory["weak_concepts"], recurring]):
            return None
        return memory

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
                session = self._fresh_session(lesson, self.outline_for(lesson, db), db=db)
                self._rehydrate_plan(session, lesson)
                session.evaluation_history = self._history_from_db(lesson)
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
            for key in [k for k in self._render_jobs if k[0] == lesson_id]:
                del self._render_jobs[key]

    # -- FSM driving ---------------------------------------------------------

    def build_plan(self, lesson: Lesson, db=None) -> Any:
        """Run UNDERSTAND then PLAN, returning the generated LessonPlan."""
        outline = self.outline_for(lesson, db)
        with self._lock:
            self.reset(lesson.id)
            self._fresh_session(lesson, outline, db=db)
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
            "attempts": getattr(session, "recent_retrieval_attempts", 1),
            "refined_query": getattr(session, "recent_refined_query", None),
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
        if lesson.nodes and lesson.current_node_index >= len(lesson.nodes):
            return TeacherState.DONE  # e.g. the last concept was skipped
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
