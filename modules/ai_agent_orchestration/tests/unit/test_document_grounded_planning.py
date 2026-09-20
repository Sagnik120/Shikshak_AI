"""A document-sourced lesson must be planned from that document.

The orchestrator used to default a missing topic to "Newton's First Law" and
never showed the planner the document, so uploading a biology chapter produced a
physics lesson.
"""
import pytest

from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints
from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
from modules.ai_agent_orchestration.src.state_machine.session_state import SessionState
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState

OUTLINE = {
    "document_id": "doc-1",
    "chapters": ["Chapter 3: Photosynthesis", "3.2 The Overall Equation"],
    "key_terms": ["chlorophyll", "chloroplast", "glucose", "stomata"],
    "excerpts": ["Photosynthesis converts light energy into chemical energy stored as glucose."],
}

CONSTRAINTS = LearnerConstraints(level="beginner", language="en", time_budget_min=10)


class RecordingPlanner(PlannerAgent):
    """Captures what the planner was asked to plan, without calling a model."""

    def __init__(self):
        self.received = None

    def plan_lesson(self, **kwargs):
        self.received = kwargs
        from modules.ai_agent_orchestration.src.schemas.lesson import LessonNode, LessonPlan

        return LessonPlan(
            lesson_id="plan-1",
            source=kwargs.get("source_type", "topic"),
            constraints=kwargs["constraints"],
            nodes=[
                LessonNode(
                    node_id="node-1",
                    concept="Photosynthesis basics",
                    depth="intro",
                    est_minutes=3,
                    visual_type="diagram",
                    checkpoint_question=True,
                )
            ],
        )


class StubRAG:
    def __init__(self, chunks=None):
        self.chunks = chunks or []
        self.queries = []

    def retrieve_context(self, document_id, concept):
        self.queries.append((document_id, concept))
        return list(self.chunks)


def _orchestrator(planner, rag=None):
    return TeacherOrchestrator(
        planner=planner,
        explainer=object(),
        questioner=object(),
        controller=object(),
        assessor=object(),
        rag_client=rag or StubRAG(),
        ml_core_client=object(),
        avatar_client=object(),
    )


def test_understand_rejects_a_session_with_no_source():
    """Defaulting to a hardcoded topic taught the wrong subject silently."""
    orchestrator = _orchestrator(RecordingPlanner())
    session = SessionState(session_id="s1")

    with pytest.raises(ValueError, match="topic or a document_id"):
        orchestrator.step(
            TeacherState.UNDERSTAND, session, {"constraints": CONSTRAINTS, "topic": None}
        )


def test_understand_accepts_a_document_without_a_topic():
    orchestrator = _orchestrator(RecordingPlanner())
    session = SessionState(session_id="s1")

    state, _ = orchestrator.step(
        TeacherState.UNDERSTAND,
        session,
        {"constraints": CONSTRAINTS, "topic": None, "document_id": "doc-1",
         "document_outline": OUTLINE},
    )
    assert state == TeacherState.PLAN
    assert session.topic is None, "a document lesson must not be given an invented topic"
    assert session.document_outline == OUTLINE


def test_planner_receives_the_document_outline():
    planner = RecordingPlanner()
    orchestrator = _orchestrator(planner)
    session = SessionState(session_id="s1")

    state, _ = orchestrator.step(
        TeacherState.UNDERSTAND,
        session,
        {"constraints": CONSTRAINTS, "topic": None, "document_id": "doc-1",
         "document_outline": OUTLINE},
    )
    orchestrator.step(state, session, {})

    assert planner.received["source_type"] == "document"
    assert planner.received["document_outline"] == OUTLINE
    assert planner.received["topic"] is None


def test_topic_lessons_still_plan_from_the_topic():
    planner = RecordingPlanner()
    orchestrator = _orchestrator(planner)
    session = SessionState(session_id="s1")

    state, _ = orchestrator.step(
        TeacherState.UNDERSTAND,
        session,
        {"constraints": CONSTRAINTS, "topic": "Newton's Laws", "document_id": None},
    )
    orchestrator.step(state, session, {})

    assert planner.received["source_type"] == "topic"
    assert planner.received["topic"] == "Newton's Laws"
    assert planner.received["document_outline"] is None


def test_planner_prompt_includes_the_document_and_a_grounding_instruction():
    """The outline has to reach the model, not just the function signature."""
    captured = {}

    class CapturingPlanner(PlannerAgent):
        def __init__(self):
            pass

        def load_prompt(self, name):
            return "system"

        def call_llm_json(self, system_prompt, user_prompt, response_model, max_retries=2):
            captured["user_prompt"] = user_prompt
            from modules.ai_agent_orchestration.src.schemas.lesson import LessonNode, LessonPlan

            return LessonPlan(
                lesson_id="p", source="document", constraints=CONSTRAINTS,
                nodes=[LessonNode(node_id="n1", concept="c", depth="intro",
                                  est_minutes=2, visual_type="diagram",
                                  checkpoint_question=False)],
            )

    CapturingPlanner().plan_lesson(
        constraints=CONSTRAINTS, source_type="document", document_outline=OUTLINE
    )

    prompt = captured["user_prompt"]
    assert "Photosynthesis" in prompt
    assert "chlorophyll" in prompt
    assert "strictly from the supplied document" in prompt
