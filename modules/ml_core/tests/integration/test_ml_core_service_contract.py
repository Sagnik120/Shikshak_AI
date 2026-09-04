import json
from unittest.mock import patch
from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
from modules.ml_core.src.service import MLCoreService
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter
from modules.ml_core.src.schemas.evaluation import EvaluationResult

@patch("modules.ml_core.src.answer_evaluation.freeform_evaluator.get_similarity")
def test_ml_core_service_evaluate_answer(mock_sim):
    mock_sim.return_value = 0.9 # High similarity -> correct
    
    fake_llm = FakeLLMAdapter()
    service = MLCoreService(llm_adapter=fake_llm)
    
    response = StudentResponse(node_id="node_1", raw_answer="Mass is inertia", response_type="freeform", response_time_sec=10)
    
    result = service.evaluate_answer(response, expected_concept="Mass is a measure of inertia.")
    
    assert isinstance(result, EvaluationResult)
    assert result.node_id == "node_1"
    assert result.correct is True
