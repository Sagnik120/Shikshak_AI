import pytest
from fastapi.testclient import TestClient
from modules.ai_agent_orchestration.tests.web_test.server import app
from modules.ai_agent_orchestration.tests.web_test.logger import test_logger

client = TestClient(app)


def test_testbed_status_endpoint():
    """Verify /api/test/status endpoint returns valid health info."""
    response = client.get("/api/test/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["server_port"] == 8001
    assert "log_counts" in data
    assert "planner" in data["log_counts"]


def test_testbed_planner_endpoint():
    """Verify POST /api/test/planner runs with SmartMock and creates a log."""
    payload = {
        "topic": "Newton's Third Law",
        "level": "beginner",
        "language": "en",
        "time_budget_min": 15,
        "style": "conceptual",
        "use_live_llm": False
    }
    response = client.post("/api/test/planner", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "run_id" in data
    assert "plan" in data
    assert len(data["plan"]["nodes"]) >= 1

    # Verify log was created
    recent_logs = test_logger.list_recent_logs(category="planner", limit=5)
    assert any(log["run_id"] == data["run_id"] for log in recent_logs)


def test_testbed_explainer_endpoint():
    """Verify POST /api/test/explainer generates segment and writes log."""
    payload = {
        "concept": "Action and Reaction Forces",
        "depth": "core",
        "visual_type": "diagram",
        "level": "beginner",
        "language": "en",
        "time_budget_min": 15,
        "use_live_llm": False
    }
    response = client.post("/api/test/explainer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "segment" in data
    assert data["segment"]["script_text"]
    assert data["segment"]["visual_spec"]["type"] == "diagram"


def test_testbed_questioner_endpoint():
    """Verify POST /api/test/questioner synthesizes question and writes log."""
    payload = {
        "concept": "Action and Reaction Forces",
        "depth": "core",
        "visual_type": "diagram",
        "use_live_llm": False
    }
    response = client.post("/api/test/questioner", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "question" in data
    assert data["question"]["question_text"]
    assert "expected_concept" in data["question"]


def test_testbed_adaptation_endpoint():
    """Verify POST /api/test/adaptation evaluates 4-tier decision rules."""
    # Test MODIFY on 1st failure
    payload = {
        "node_id": "test_node_3",
        "correct": False,
        "partial_credit": 0.0,
        "misconception_tag": "force_velocity_confusion",
        "confidence": 0.85,
        "feedback_text": "Failed test answer",
        "consecutive_failures_on_node": 1
    }
    response = client.post("/api/test/adaptation", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"]["action"] == "MODIFY"

    # Test REGENERATE on 2nd failure
    payload["consecutive_failures_on_node"] = 2
    response = client.post("/api/test/adaptation", json=payload)
    assert response.status_code == 200
    assert response.json()["decision"]["action"] == "REGENERATE"

    # Test HUMAN on 3rd failure
    payload["consecutive_failures_on_node"] = 3
    response = client.post("/api/test/adaptation", json=payload)
    assert response.status_code == 200
    assert response.json()["decision"]["action"] == "HUMAN"


def test_testbed_fsm_step_endpoint():
    """Verify POST /api/test/fsm/step executes FSM transition."""
    payload = {
        "session_id": "pytest_fsm_session_01",
        "current_state": "UNDERSTAND",
        "inputs": {
            "topic": "Thermodynamics",
            "constraints": {
                "level": "beginner",
                "language": "en",
                "time_budget_min": 15
            }
        },
        "use_live_llm": False
    }
    response = client.post("/api/test/fsm/step", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["previous_state"] == "UNDERSTAND"
    assert data["next_state"] == "PLAN"


def test_testbed_logs_retrieval():
    """Verify GET /api/test/logs and detail retrieval."""
    response = client.get("/api/test/logs?limit=10")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)

    if logs:
        first_log = logs[0]
        cat = first_log["category"]
        filename = first_log["filename"]

        detail_resp = client.get(f"/api/test/logs/{cat}/{filename}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert "run_id" in detail
        assert "trace" in detail
