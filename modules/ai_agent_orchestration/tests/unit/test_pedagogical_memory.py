"""Cross-lesson memory must bias planning only — never mid-lesson state.

Offline: the planner's LLM is a stub that records the prompt it was handed.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock

from modules.ai_agent_orchestration.src.agents.adaptation_controller import AdaptationController
from modules.ai_agent_orchestration.src.agents.assessment import AssessmentAgent
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints
from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
from modules.ai_agent_orchestration.src.state_machine.session_state import SessionState
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter

FIXTURES = Path(__file__).parent.parent / "fixtures" / "mock_llm_responses"

MEMORY = {
    "strong_concepts": ["Scalars and vectors"],
    "weak_concepts": ["Net force"],
    "recurring_misconceptions": ["confuses_net_force_with_total_force"],
    "lessons_completed": 2,
}


def _orchestrator(planner_adapter):
    return TeacherOrchestrator(
        PlannerAgent(planner_adapter),
        ExplainerAgent(FakeLLMAdapter([(FIXTURES / "explainer.json").read_text()] * 3)),
        QuestionerAgent(FakeLLMAdapter([(FIXTURES / "questioner.json").read_text()] * 3)),
        AdaptationController(),
        AssessmentAgent(FakeLLMAdapter([(FIXTURES / "assessment.json").read_text()])),
        MagicMock(**{"retrieve_context.return_value": []}),
        MagicMock(),
        MagicMock(**{"render_segment.return_value": "job_1"}),
    )


def _session(**kwargs) -> SessionState:
    session = SessionState(session_id="lesson-1")
    session.constraints = LearnerConstraints(level="beginner", language="en", time_budget_min=5)
    session.topic = "Newton's Laws"
    for key, value in kwargs.items():
        setattr(session, key, value)
    return session


def _planner_prompt(adapter) -> str:
    """The user-side prompt the planner actually sent."""
    return adapter.calls[0][-1]["content"]


def test_memory_reaches_the_planner_prompt_at_plan_time():
    adapter = FakeLLMAdapter([(FIXTURES / "planner.json").read_text()])
    orchestrator = _orchestrator(adapter)
    session = _session(learner_profile=MEMORY)

    orchestrator.step(TeacherState.PLAN, session, {})

    payload = json.loads(_planner_prompt(adapter).split("\n", 1)[1])
    assert payload["learner_profile"]["weak_concepts"] == ["Net force"]
    assert payload["learner_profile"]["recurring_misconceptions"] == [
        "confuses_net_force_with_total_force"
    ]


def test_a_learner_with_no_history_plans_exactly_as_before():
    """First-ever lesson must behave identically to the pre-memory system."""
    adapter = FakeLLMAdapter([(FIXTURES / "planner.json").read_text()])
    orchestrator = _orchestrator(adapter)

    orchestrator.step(TeacherState.PLAN, _session(learner_profile=None), {})

    assert "learner_profile" not in json.loads(_planner_prompt(adapter).split("\n", 1)[1])


def test_memory_is_never_consulted_after_planning():
    """Teaching, questioning and adapting must not read cross-lesson memory."""
    adapter = FakeLLMAdapter([(FIXTURES / "planner.json").read_text()])
    orchestrator = _orchestrator(adapter)
    session = _session(learner_profile=MEMORY)

    state, _ = orchestrator.step(TeacherState.PLAN, session, {})

    # A sentinel that raises if anything downstream touches the profile.
    class Tripwire(dict):
        def __getitem__(self, key):  # pragma: no cover - only on failure
            raise AssertionError("learner_profile was read after PLAN")

        def get(self, *args, **kwargs):  # pragma: no cover - only on failure
            raise AssertionError("learner_profile was read after PLAN")

    session.learner_profile = Tripwire()

    state, segment = orchestrator.step(state, session, {})           # EXPLAIN
    state, _ = orchestrator.step(state, session, {"segment": segment})  # DEMONSTRATE
    orchestrator.step(state, session, {})                             # QUESTION


def test_planning_does_not_mutate_memory():
    adapter = FakeLLMAdapter([(FIXTURES / "planner.json").read_text()])
    orchestrator = _orchestrator(adapter)
    session = _session(learner_profile=dict(MEMORY))

    orchestrator.step(TeacherState.PLAN, session, {})

    assert session.learner_profile == MEMORY
