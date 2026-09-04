import pytest
from unittest.mock import MagicMock
from modules.ai_agent_orchestration.src.integration.ml_core_client import MLCoreClient
from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult

def test_ml_core_stub_raises():
    client = MLCoreClient()
    response = StudentResponse(node_id="n1", raw_answer="hello", response_type="text", response_time_sec=1.5)
    with pytest.raises(NotImplementedError):
        client.evaluate_answer(response)
        
def test_orchestrator_handles_mocked_eval_result():
    from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
    from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
    from modules.ai_agent_orchestration.src.state_machine.session_state import SessionState
    
    mock_controller = MagicMock()
    decision = MagicMock()
    decision.action = "ALLOW"
    decision.reason = "Correct."
    mock_controller.decide.return_value = decision
    
    # We bypass ml_core client and feed the orchestrator an evaluation result directly in EVALUATE
    orchestrator = TeacherOrchestrator(None, None, None, mock_controller, None, None, None, None)
    
    session = SessionState("test_session")
    
    eval_result = EvaluationResult(node_id="n1", correct=True, confidence=0.9, partial_credit=0.0, feedback_text="")
    
    next_state, payload = orchestrator.step(TeacherState.ADAPT, session, {"eval_result": eval_result})
    
    assert next_state == TeacherState.CONTINUE
    assert payload.action == "ALLOW"
