import pytest
from unittest.mock import patch
from modules.backend.src.persistence.in_memory import session_repo
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState

def test_create_session(client):
    response = client.post("/api/v1/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "token" in data
    assert session_repo.get_session_token(data["session_id"]) == data["token"]

def test_submit_topic(client):
    # Setup
    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "session_id": session_id,
        "topic": "Newton's Laws",
        "constraints": {
            "level": "beginner",
            "language": "en",
            "time_budget_min": 15
        }
    }
    
    # Valid submission
    response = client.post(f"/api/v1/sessions/{session_id}/topic", json=payload, headers=headers)
    assert response.status_code == 200
    
    # Invalid token submission
    response = client.post(f"/api/v1/sessions/{session_id}/topic", json=payload, headers={"Authorization": "Bearer badtoken"})
    assert response.status_code == 401
    
    # Verify persistence
    topic, constraints = session_repo.get_topic_and_constraints(session_id)
    assert topic == "Newton's Laws"

def test_generate_plan(client, mock_ai_service):
    ai_mock, avatar_mock = mock_ai_service
    
    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Set up topic
    session_repo.save_topic(session_id, "Gravity", {"level": "beginner", "language": "en", "time_budget_min": 10})
    
    # Setup mock behavior
    # driver.step returns (TeacherState, payload)
    mock_plan = {
        "lesson_id": "l1",
        "source": "topic",
        "constraints": {"level": "beginner", "language": "en", "time_budget_min": 10},
        "nodes": []
    }
    ai_mock.process_next_step.side_effect = [
        (TeacherState.PLAN, None), # UNDERSTAND -> PLAN
        (TeacherState.EXPLAIN, mock_plan) # PLAN -> EXPLAIN
    ]
    
    response = client.post(f"/api/v1/sessions/{session_id}/plan", headers=headers)
    assert response.status_code == 200
    assert response.json()["lesson_id"] == "l1"
    
    # Verify Orchestrator was called
    assert ai_mock.process_next_step.call_count == 2
