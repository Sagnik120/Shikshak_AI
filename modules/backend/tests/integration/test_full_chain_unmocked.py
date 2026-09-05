"""
Full Un-Mocked End-to-End System Integration Test.
Exercises the entire production chain without ANY test doubles or mocks:
Real Backend API -> Real SessionDriver -> Real AIOperationService ->
Real TeacherOrchestrator -> Real PlannerAgent -> Real ExplainerAgent ->
Real AvatarVoiceService -> Real QuestionerAgent -> Real MLCoreService ->
Real AdaptationController -> Real AssessmentAgent -> Real WebSocket Relay.
"""

import pytest
from fastapi.testclient import TestClient
from modules.backend.src.main import app
from modules.backend.src.persistence.in_memory import session_repo


def test_full_chain_unmocked_teaching_journey():
    """
    Executes a complete lesson lifecycle across all 5 integrated modules
    using the production container without any mocks.
    """
    client = TestClient(app)

    # 1. Create Session via Real Backend Auth & Persistence
    resp = client.post("/api/v1/sessions")
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    token = data["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit Real Topic with Constraints
    topic_payload = {
        "session_id": session_id,
        "topic": "Newton's First Law of Motion",
        "constraints": {
            "level": "beginner",
            "language": "en",
            "time_budget_min": 10,
            "style": "intuitive"
        }
    }
    topic_resp = client.post(f"/api/v1/sessions/{session_id}/topic", json=topic_payload, headers=headers)
    assert topic_resp.status_code == 200
    assert topic_resp.json()["status"] == "success"

    # 3. Generate Real Plan via Real PlannerAgent
    plan_resp = client.post(f"/api/v1/sessions/{session_id}/plan", headers=headers)
    assert plan_resp.status_code == 200
    plan = plan_resp.json()
    assert "lesson_id" in plan
    assert len(plan["nodes"]) >= 1
    assert plan["nodes"][0]["concept"] != ""

    # Verify session state checkpoint was recorded
    state_record = session_repo.get_state(session_id)
    assert state_record is not None
    assert state_record.get("current_state") == "PLANNED"

    # 4. Connect Live WebSocket to Exercise Orchestration + Avatar + ML Core
    # Note: We connect using the real WebSocket endpoint without mock_ai_service
    with client.websocket_connect(f"/api/v1/sessions/{session_id}/live?token={token}") as ws:
        # Receive video segments and progress until interaction_event arrives
        events = []
        q_payload = None
        for _ in range(10):
            msg = ws.receive_json()
            events.append(msg["event_type"])
            if msg["event_type"] == "interaction_event":
                q_payload = msg["payload"]
                break

        assert "video_segment" in events, f"Expected at least one video_segment in {events}"
        assert q_payload is not None, f"Expected interaction_event in {events}"
        assert "question_text" in q_payload
        assert len(q_payload["question_text"]) > 0
        node_id = q_payload["node_id"]

        # 5. Submit Real Student Answer
        # Send an answer matching the expected concept to trigger ALLOW
        student_answer = {
            "event_type": "student_response",
            "payload": {
                "node_id": node_id,
                "raw_answer": q_payload.get("expected_concept", "First Law of Thermodynamics"),
                "response_type": "mcq",
                "response_time_sec": 4.5
            }
        }
        ws.send_json(student_answer)

        # Event 3: Real Evaluation from MLCoreService
        eval_msg = ws.receive_json()
        assert eval_msg["event_type"] == "evaluation_result"
        eval_payload = eval_msg["payload"]
        assert "correct" in eval_payload
        assert "confidence" in eval_payload

        # Event 4: Real Pedagogical Decision from AdaptationController
        adapt_msg = ws.receive_json()
        assert adapt_msg["event_type"] == "adaptation_decision"
        adapt_payload = adapt_msg["payload"]
        assert adapt_payload["action"] in ("ALLOW", "MODIFY", "REGENERATE", "HUMAN")

        # Event 5: Real Final Assessment Report from AssessmentAgent
        report_msg = None
        for _ in range(10):
            msg = ws.receive_json()
            if msg["event_type"] == "assessment_report":
                report_msg = msg
                break
        assert report_msg is not None, "Expected assessment_report to arrive after lesson completion"
        assert report_msg["event_type"] == "assessment_report"
        report_payload = report_msg["payload"]
        assert "score_pct" in report_payload
        assert 0.0 <= report_payload["score_pct"] <= 100.0
        assert "narrative_feedback" in report_payload
