import json
from pathlib import Path
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter
from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def load_mock(filename: str) -> str:
    with open(FIXTURES_DIR / "mock_llm_responses" / filename, "r", encoding="utf-8") as f:
        return f.read()

def test_planner_valid_response():
    mock_resp = load_mock("planner.json")
    adapter = FakeLLMAdapter(responses=[mock_resp])
    planner = PlannerAgent(adapter)
    
    constraints = LearnerConstraints(level="beginner", language="English", time_budget_min=15, style="visual")
    plan = planner.plan_lesson(constraints=constraints, source_type="topic", topic="Gravity")
    
    assert plan.lesson_id == "lesson_abc"
    assert len(plan.nodes) == 2

def test_planner_time_budget_variants():
    # Verify the agent passes the constraint through in the prompt correctly
    mock_resp = load_mock("planner.json")
    adapter = FakeLLMAdapter(responses=[mock_resp, mock_resp])
    planner = PlannerAgent(adapter)
    
    c1 = LearnerConstraints(level="beginner", language="English", time_budget_min=5, style="visual")
    planner.plan_lesson(constraints=c1, source_type="topic", topic="Gravity")
    assert '"time_budget_min": 5' in adapter.calls[0][1]["content"]
    
    c2 = LearnerConstraints(level="beginner", language="English", time_budget_min="multi_day_plan", style="visual")
    planner.plan_lesson(constraints=c2, source_type="topic", topic="Gravity")
    assert '"time_budget_min": "multi_day_plan"' in adapter.calls[1][1]["content"]
