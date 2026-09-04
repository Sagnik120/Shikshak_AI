import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints, LessonPlan
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def load_fixture(filename: str) -> dict:
    with open(FIXTURES_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)

def test_learner_constraints_schema():
    data = load_fixture("sample_learner_constraints.json")
    constraints = LearnerConstraints(**data)
    assert constraints.level == "beginner"
    assert constraints.language == "English"
    
    # Test rejection on missing field
    del data["level"]
    with pytest.raises(ValidationError):
        LearnerConstraints(**data)

def test_lesson_plan_schema():
    data = load_fixture("sample_lesson_plan.json")
    plan = LessonPlan(**data)
    assert plan.lesson_id == "lesson_abc"
    assert len(plan.nodes) == 2
    assert plan.nodes[0].node_id == "node_1"

def test_evaluation_result_schema():
    data = load_fixture("sample_evaluation_results.json")["correct"][0]
    result = EvaluationResult(**data)
    assert result.correct is True
    assert result.confidence == 0.9
