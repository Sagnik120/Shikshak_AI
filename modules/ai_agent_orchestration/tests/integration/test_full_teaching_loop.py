import json
from pathlib import Path
from unittest.mock import MagicMock
from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.ai_agent_orchestration.src.state_machine.session_state import SessionState
from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.agents.assessment import AssessmentAgent
from modules.ai_agent_orchestration.src.agents.adaptation_controller import AdaptationController
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def load_mock(filename: str) -> str:
    with open(FIXTURES_DIR / "mock_llm_responses" / filename, "r", encoding="utf-8") as f:
        return f.read()

def test_full_teaching_loop():
    planner_adapter = FakeLLMAdapter([load_mock("planner.json")])
    explainer_adapter = FakeLLMAdapter([load_mock("explainer.json")] * 5)
    questioner_adapter = FakeLLMAdapter([load_mock("questioner.json")] * 5)
    assessment_adapter = FakeLLMAdapter([load_mock("assessment.json")])
    
    planner = PlannerAgent(planner_adapter)
    explainer = ExplainerAgent(explainer_adapter)
    questioner = QuestionerAgent(questioner_adapter)
    assessor = AssessmentAgent(assessment_adapter)
    controller = AdaptationController()
    
    mock_rag = MagicMock()
    mock_rag.retrieve_context.return_value = []
    
    mock_avatar = MagicMock()
    mock_avatar.render_segment.return_value = "job_123"
    
    orchestrator = TeacherOrchestrator(planner, explainer, questioner, controller, assessor, mock_rag, None, mock_avatar)
    session = SessionState("test_session")
    
    # 1. UNDERSTAND
    constraints = LearnerConstraints(level="beginner", language="English", time_budget_min=15, style="visual")
    state, _ = orchestrator.step(TeacherState.UNDERSTAND, session, {"constraints": constraints, "topic": "Gravity"})
    assert state == TeacherState.PLAN
    
    # 2. PLAN
    state, plan = orchestrator.step(state, session, {})
    assert state == TeacherState.EXPLAIN
    assert len(plan.nodes) == 2
    
    # 3. EXPLAIN (Node 1)
    state, segment = orchestrator.step(state, session, {})
    assert state == TeacherState.DEMONSTRATE
    
    # 4. DEMONSTRATE
    state, job = orchestrator.step(state, session, {"segment": segment})
    assert state == TeacherState.QUESTION
    
    # 5. QUESTION
    state, event = orchestrator.step(state, session, {"segment": segment})
    assert state == TeacherState.EVALUATE
    
    # 6. EVALUATE (Simulate correct response)
    # Since ML core is missing, we bypass EVALUATE step and pretend it generated a correct eval
    eval_result = EvaluationResult(node_id="node_1", correct=True, confidence=0.9, partial_credit=0.0, feedback_text="")
    session.evaluation_history.append(eval_result)
    state = TeacherState.ADAPT
    
    # 7. ADAPT (Correct -> ALLOW -> CONTINUE)
    state, decision = orchestrator.step(state, session, {"eval_result": eval_result})
    assert state == TeacherState.CONTINUE
    
    # 8. CONTINUE (moves to Node 2)
    state, _ = orchestrator.step(state, session, {})
    assert state == TeacherState.EXPLAIN
    assert session.current_node_index == 1
    
    # 9. EXPLAIN (Node 2)
    state, segment = orchestrator.step(state, session, {})
    assert state == TeacherState.DEMONSTRATE
    
    # 10. DEMONSTRATE
    state, job = orchestrator.step(state, session, {"segment": segment})
    assert state == TeacherState.QUESTION
    
    # 11. QUESTION
    state, event = orchestrator.step(state, session, {"segment": segment})
    assert state == TeacherState.EVALUATE
    
    # 12. EVALUATE (Simulate incorrect response with misconception)
    eval_result2 = EvaluationResult(node_id="node_2", correct=False, confidence=0.8, partial_credit=0.0, misconception_tag="mixed_up", feedback_text="")
    session.evaluation_history.append(eval_result2)
    state = TeacherState.ADAPT
    
    # 13. ADAPT (Incorrect -> MODIFY -> EXPLAIN)
    state, decision2 = orchestrator.step(state, session, {"eval_result": eval_result2})
    assert state == TeacherState.EXPLAIN
    assert session.current_feedback_override is not None
    
    # 14. EXPLAIN (Node 2, modified)
    state, segment_mod = orchestrator.step(state, session, {})
    # Check that feedback override was passed to LLM
    assert "mixed_up" in explainer_adapter.calls[-1][1]["content"]
    assert state == TeacherState.DEMONSTRATE
    
    # Skip to EVALUATE again (2nd try on Node 2)
    state = TeacherState.ADAPT
    eval_result3 = EvaluationResult(node_id="node_2", correct=False, confidence=0.8, partial_credit=0.0, feedback_text="")
    session.evaluation_history.append(eval_result3)
    
    # 15. ADAPT (2nd consecutive failure -> REGENERATE)
    state, decision3 = orchestrator.step(state, session, {"eval_result": eval_result3})
    assert state == TeacherState.PLAN
    assert decision3.action == "REGENERATE"
    
    # Pretend it was replanned, skipped to ADAPT again for 3rd failure
    state = TeacherState.ADAPT
    eval_result4 = EvaluationResult(node_id="node_2", correct=False, confidence=0.8, partial_credit=0.0, feedback_text="")
    session.evaluation_history.append(eval_result4)
    
    # 16. ADAPT (3rd failure -> HUMAN)
    state, decision4 = orchestrator.step(state, session, {"eval_result": eval_result4})
    assert state == TeacherState.HUMAN_ESCALATION
