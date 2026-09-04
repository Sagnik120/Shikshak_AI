import json
import pytest
from unittest.mock import patch
from modules.ml_core.src.answer_evaluation.freeform_evaluator import FreeformEvaluator
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter

@patch("modules.ml_core.src.answer_evaluation.freeform_evaluator.get_similarity")
def test_freeform_confident_high(mock_sim):
    # Mock similarity to be high (e.g. 0.9)
    mock_sim.return_value = 0.9
    fake_llm = FakeLLMAdapter() # Shouldn't be called
    evaluator = FreeformEvaluator(fake_llm)
    
    result = evaluator.evaluate("node_1", "Yes, mass is inertia.", "Mass is a measure of inertia.")
    
    assert result.correct is True
    assert result.confidence == 0.9
    assert len(fake_llm.calls) == 0

@patch("modules.ml_core.src.answer_evaluation.freeform_evaluator.get_similarity")
def test_freeform_confident_low(mock_sim):
    # Mock similarity to be low (e.g. 0.2)
    mock_sim.return_value = 0.2
    fake_llm = FakeLLMAdapter() # Shouldn't be called
    evaluator = FreeformEvaluator(fake_llm)
    
    result = evaluator.evaluate("node_1", "Wrong answer.", "Mass is a measure of inertia.")
    
    assert result.correct is False
    assert result.confidence == 0.8
    assert len(fake_llm.calls) == 0

@patch("modules.ml_core.src.answer_evaluation.freeform_evaluator.get_similarity")
def test_freeform_ambiguous_llm_judge(mock_sim):
    # Mock similarity to be mid-range (e.g. 0.5)
    mock_sim.return_value = 0.5
    llm_resp = json.dumps({"correct": False, "partial_credit": 0.5, "feedback_text": "Close."})
    fake_llm = FakeLLMAdapter([llm_resp])
    
    evaluator = FreeformEvaluator(fake_llm)
    result = evaluator.evaluate("node_1", "It is kinda like weight.", "Mass is a measure of inertia.")
    
    assert result.correct is False
    assert result.partial_credit == 0.5
    assert result.feedback_text == "Close."
    assert len(fake_llm.calls) == 1

@patch("modules.ml_core.src.answer_evaluation.freeform_evaluator.get_similarity")
def test_freeform_ambiguous_llm_malformed(mock_sim):
    mock_sim.return_value = 0.5
    # Malformed JSON triggers fallback handling
    fake_llm = FakeLLMAdapter(["NOT JSON"])
    
    evaluator = FreeformEvaluator(fake_llm)
    result = evaluator.evaluate("node_1", "It is kinda like weight.", "Mass is a measure of inertia.")
    
    assert result.correct is False
    assert result.confidence == 0.5
    # LLM failed, fallback feedback applies
    assert "could not evaluate" in result.feedback_text.lower()
