import json
from pathlib import Path
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter
from modules.ai_agent_orchestration.src.agents.assessment import AssessmentAgent
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def load_mock(filename: str) -> str:
    with open(FIXTURES_DIR / "mock_llm_responses" / filename, "r", encoding="utf-8") as f:
        return f.read()

def test_assessment_valid_response():
    mock_resp = load_mock("assessment.json")
    adapter = FakeLLMAdapter(responses=[mock_resp])
    assessor = AssessmentAgent(adapter)
    
    history = [
        EvaluationResult(node_id="n1", correct=True, confidence=0.9, partial_credit=0.0, feedback_text="ok")
    ]
    
    report = assessor.generate_report(lesson_id="lesson_abc", session_history=history)
    
    assert report.lesson_id == "lesson_abc"
    assert report.score_pct == 95.0
    assert "Kinematics" in report.strong_areas
