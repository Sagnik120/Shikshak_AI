"""The LangGraph runtime must behave identically to the built-in dispatcher.

Phase 2's acceptance criterion: every FSM transition and every ADAPT branch
behaves the same under the adapter, verified offline on identical fixtures. The
original dispatcher stays the default, so these tests are what justify allowing
the switch at all.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from modules.ai_agent_orchestration.src.agents.adaptation_controller import AdaptationController
from modules.ai_agent_orchestration.src.agents.assessment import AssessmentAgent
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult
from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints
from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
from modules.ai_agent_orchestration.src.state_machine.session_state import SessionState
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.ai_agent_orchestration.src.state_machine.transitions import VALID_TRANSITIONS
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter

langgraph_adapter = pytest.importorskip(
    "modules.ai_agent_orchestration.src.state_machine.langgraph_adapter",
    reason="LangGraph is an optional runtime",
)
LangGraphOrchestrator = langgraph_adapter.LangGraphOrchestrator
build_orchestration_runtime = langgraph_adapter.build_orchestration_runtime

FIXTURES = Path(__file__).parent.parent / "fixtures" / "mock_llm_responses"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text()


def _fsm() -> TeacherOrchestrator:
    """A dispatcher with deterministic canned agents — no LLM, no network."""
    return TeacherOrchestrator(
        PlannerAgent(FakeLLMAdapter([_load("planner.json")] * 4)),
        ExplainerAgent(FakeLLMAdapter([_load("explainer.json")] * 8)),
        QuestionerAgent(FakeLLMAdapter([_load("questioner.json")] * 8)),
        AdaptationController(),
        AssessmentAgent(FakeLLMAdapter([_load("assessment.json")] * 4)),
        MagicMock(**{"retrieve_context.return_value": []}),
        MagicMock(),
        MagicMock(**{"render_segment.return_value": "job_1"}),
    )


def _session() -> SessionState:
    session = SessionState(session_id="parity-1")
    session.constraints = LearnerConstraints(level="beginner", language="en", time_budget_min=5)
    session.topic = "Newton's Laws"
    return session


def _evaluation(correct: bool, node_id: str = "node_1", tag=None) -> EvaluationResult:
    return EvaluationResult(
        node_id=node_id,
        correct=correct,
        partial_credit=1.0 if correct else 0.0,
        confidence=0.9,
        misconception_tag=tag,
        feedback_text="fixture",
    )


def _run_teaching_sequence(orchestrator) -> list:
    """Drive UNDERSTAND→…→QUESTION and record every transition."""
    session, transitions = _session(), []
    state = TeacherState.UNDERSTAND

    state, _ = orchestrator.step(
        state, session, {"constraints": session.constraints, "topic": session.topic}
    )
    transitions.append(state.name)

    state, plan = orchestrator.step(state, session, {})           # PLAN
    transitions.append(f"{state.name}:nodes={len(plan.nodes)}")

    state, segment = orchestrator.step(state, session, {})        # EXPLAIN
    transitions.append(f"{state.name}:{segment.node_id}")

    state, payload = orchestrator.step(state, session, {"segment": segment})  # DEMONSTRATE
    transitions.append(f"{state.name}:{payload}")

    state, question = orchestrator.step(state, session, {})       # QUESTION
    transitions.append(f"{state.name}:{question.type}")

    return transitions


def test_the_graph_mirrors_the_declared_fsm_topology():
    graph = LangGraphOrchestrator(_fsm()).graph
    nodes = {name for name in graph.nodes if not name.startswith("__")}

    assert nodes == {state.name.lower() for state in TeacherState}


def test_teaching_sequence_is_identical_under_both_runtimes():
    assert _run_teaching_sequence(_fsm()) == _run_teaching_sequence(LangGraphOrchestrator(_fsm()))


@pytest.mark.parametrize(
    "history_builder, expected_action",
    [
        (lambda: [_evaluation(True)], "ALLOW"),
        (lambda: [_evaluation(False, tag="confuses_force")], "MODIFY"),
        (lambda: [_evaluation(False) for _ in range(3)], "REGENERATE"),
        (lambda: [_evaluation(False) for _ in range(4)], "HUMAN"),
    ],
)
def test_every_adapt_branch_matches(history_builder, expected_action):
    """ALLOW / MODIFY / REGENERATE / HUMAN must route the same in both runtimes."""
    results = []
    for orchestrator in (_fsm(), LangGraphOrchestrator(_fsm())):
        session = _session()
        session.evaluation_history = history_builder()
        state, decision = orchestrator.step(
            TeacherState.ADAPT, session, {"eval_result": session.evaluation_history[-1]}
        )
        results.append((state.name, decision.action))

    assert results[0] == results[1]
    assert results[0][1] == expected_action


def test_evaluate_step_matches():
    results = []
    for orchestrator in (_fsm(), LangGraphOrchestrator(_fsm())):
        session = _session()
        orchestrator.ml_core = MagicMock()
        orchestrator.ml_core.evaluate_answer.return_value = _evaluation(False, tag="tag")
        state, evaluation = orchestrator.step(
            TeacherState.EVALUATE,
            session,
            {
                "student_response": StudentResponse(
                    node_id="node_1", raw_answer="x", response_type="mcq", response_time_sec=1.0
                )
            },
        )
        results.append((state.name, evaluation.correct, evaluation.misconception_tag))

    assert results[0] == results[1]


def test_an_invalid_transition_still_raises_under_langgraph():
    """The graph must not become a way to bypass VALID_TRANSITIONS."""
    orchestrator = LangGraphOrchestrator(_fsm())
    session = _session()

    with pytest.raises(Exception):
        # QUESTION cannot run before a plan exists.
        orchestrator.step(TeacherState.QUESTION, session, {})


def test_agents_are_reused_not_reimplemented():
    """The adapter must delegate, never duplicate agent logic."""
    fsm = _fsm()
    graph_runtime = LangGraphOrchestrator(fsm)

    for attr in ("planner", "explainer", "questioner", "controller", "assessor"):
        assert getattr(graph_runtime, attr) is getattr(fsm, attr)


def test_runtime_selection_defaults_to_the_builtin_dispatcher():
    fsm = _fsm()
    assert build_orchestration_runtime(fsm) is fsm
    assert build_orchestration_runtime(fsm, "fsm") is fsm
    assert isinstance(build_orchestration_runtime(fsm, "langgraph"), LangGraphOrchestrator)


def test_selection_falls_back_to_the_dispatcher_if_the_graph_cannot_build(monkeypatch):
    """A missing optional dependency must never brick a deploy."""
    monkeypatch.setattr(
        langgraph_adapter, "LangGraphOrchestrator",
        MagicMock(side_effect=ImportError("langgraph not installed")),
    )
    fsm = _fsm()
    assert build_orchestration_runtime(fsm, "langgraph") is fsm
