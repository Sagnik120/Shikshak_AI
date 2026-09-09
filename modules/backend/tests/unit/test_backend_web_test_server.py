"""Unit tests for the isolated Backend Module Web Testbed Server and Hierarchical Logger.

Validates:
  1. GET /api/test/status
  2. POST /api/test/sessions
  3. POST /api/test/topic
  4. POST /api/test/upload (document ingest simulation)
  5. POST /api/test/plan (curriculum plan generation)
  6. GET /api/test/learners/{learner_id}/profile
  7. GET /api/test/logs and log reader
  8. Hierarchical logger directory structure and file persistence
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from modules.backend.tests.web_test.server import app
from modules.backend.tests.web_test.logger import BackendTestLogger


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_logger():
    temp_dir = tempfile.mkdtemp(prefix="shikshak_backend_test_logs_")
    logger_instance = BackendTestLogger(base_log_dir=temp_dir)
    yield logger_instance
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_status_endpoint(client):
    res = client.get("/api/test/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["port"] == 8005
    assert data["module"] == "backend"
    assert data["persistence"] == "in_memory"
    assert "gateways" in data


def test_sessions_endpoint(client):
    res = client.post("/api/test/sessions")
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert "token" in data
    assert data["status"] == "created"
    assert len(data["session_id"]) > 10


def test_topic_endpoint(client):
    # 1. Create session first
    res_sess = client.post("/api/test/sessions")
    session_id = res_sess.json()["session_id"]

    # 2. Submit topic
    payload = {
        "session_id": session_id,
        "topic": "Newton's First Law of Motion",
        "level": "beginner",
        "language": "en",
        "time_budget_min": 15,
    }
    res = client.post("/api/test/topic", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["topic"] == "Newton's First Law of Motion"
    assert data["constraints"]["level"] == "beginner"


def test_upload_endpoint(client):
    res_sess = client.post("/api/test/sessions")
    session_id = res_sess.json()["session_id"]

    sample_text = b"# Chapter 1: Dynamics\nForce equals mass times acceleration."
    files = {"file": ("physics.txt", sample_text, "text/plain")}
    data = {
        "session_id": session_id,
        "level": "beginner",
        "language": "en",
        "time_budget_min": "15",
    }

    res = client.post("/api/test/upload", data=data, files=files)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "ready"
    assert "document_id" in res_data
    assert res_data["filename"] == "physics.txt"
    assert res_data["size_bytes"] == len(sample_text)


def test_plan_endpoint(client):
    # Create session and submit topic
    res_sess = client.post("/api/test/sessions")
    session_id = res_sess.json()["session_id"]

    client.post("/api/test/topic", json={
        "session_id": session_id,
        "topic": "Thermodynamics Fundamentals",
        "level": "intermediate",
        "language": "en",
        "time_budget_min": 20,
    })

    # Generate plan
    res_plan = client.post("/api/test/plan", json={"session_id": session_id})
    assert res_plan.status_code == 200
    plan_data = res_plan.json()
    assert plan_data["status"] == "planned"
    assert plan_data["session_id"] == session_id
    assert "lesson_plan" in plan_data


def test_learner_profile_endpoint(client):
    res = client.get("/api/test/learners/learner_test_42/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["learner_id"] == "learner_test_42"
    assert "profile" in data
    assert "strong_concepts" in data["profile"]


def test_logs_endpoints(client):
    # Trigger an action to ensure at least one log exists
    client.post("/api/test/sessions")

    res = client.get("/api/test/logs?limit=10")
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1

    first_log = logs[0]
    category = first_log["category"]
    filename = Path(first_log["log_file"]).name

    # Inspect the specific log content
    res_detail = client.get(f"/api/test/logs/{category}/{filename}")
    assert res_detail.status_code == 200
    content_data = res_detail.json()
    assert "content" in content_data
    assert "SHIKSHAK AI" in content_data["content"]


def test_hierarchical_logger_structure(temp_logger):
    # Verify categories exist
    for cat in BackendTestLogger.CATEGORIES:
        assert (temp_logger.base_dir / cat).exists()
        assert (temp_logger.base_dir / cat / ".gitkeep").exists()

    # Write a session log entry
    meta = temp_logger.log_session_event(
        operation="test_session_create",
        session_id="sess_12345",
        input_data={"param": "value"},
        output_data={"token": "tok_xyz"},
        source_function="test_fn",
        latency_ms=1.2,
    )

    assert meta["category"] == "sessions"
    assert (temp_logger.base_dir / "sessions" / meta["filename"]).exists()
    assert (temp_logger.base_dir / "sessions" / meta["json_filename"]).exists()

    # Read log
    content = temp_logger.read_log_file("sessions", meta["filename"])
    assert content is not None
    assert "sess_12345" in content
    assert "modules/backend/src/api/rest.py" in content
