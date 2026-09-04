import pytest
from pydantic import ValidationError
from modules.ml_core.src.schemas.evaluation import EvaluationResult

def test_evaluation_result_schema_valid():
    data = {
        "node_id": "node_123",
        "correct": True,
        "partial_credit": 1.0,
        "misconception_tag": None,
        "confidence": 0.95,
        "feedback_text": "Great job!"
    }
    result = EvaluationResult(**data)
    assert result.node_id == "node_123"
    assert result.correct is True
    assert result.partial_credit == 1.0
    assert result.misconception_tag is None
    assert result.confidence == 0.95
    assert result.feedback_text == "Great job!"

def test_evaluation_result_missing_required():
    data = {
        "node_id": "node_123",
        "correct": True
        # missing feedback_text
    }
    with pytest.raises(ValidationError):
        EvaluationResult(**data)
