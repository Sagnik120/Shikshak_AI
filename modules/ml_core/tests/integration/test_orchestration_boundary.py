import pytest
from unittest.mock import patch, MagicMock
from modules.ml_core.src.service import MLCoreService
from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter

@patch("modules.ml_core.src.answer_evaluation.freeform_evaluator.get_similarity")
def test_orchestration_boundary_mocked_controller(mock_sim):
    mock_sim.return_value = 0.9
    fake_llm = FakeLLMAdapter()
    service = MLCoreService(llm_adapter=fake_llm)
    
    response = StudentResponse(node_id="node_1", raw_answer="Mass is inertia", response_type="freeform", response_time_sec=10)
    eval_result = service.evaluate_answer(response, expected_concept="Mass is a measure of inertia.")
    
    # Mocking what the AdaptationController does in Orchestration
    # A correct evaluation -> action="ALLOW"
    def adaptation_logic(eval_res):
        if eval_res.correct:
            return "ALLOW"
        return "MODIFY"
        
    action = adaptation_logic(eval_result)
    assert action == "ALLOW"
