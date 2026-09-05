import pytest
from unittest.mock import Mock
from modules.backend.src.persistence.in_memory import session_repo
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState


def test_ws_reconnect_resumes_from_persisted_checkpoint(client, mock_ai_service):
    """Verifies that disconnecting mid-lesson and reconnecting resumes from the persisted state."""
    ai_mock, avatar_mock = mock_ai_service

    # Create session
    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]

    # Pre-seed session state simulating that it already reached QUESTION
    session_repo.save_state(session_id, "QUESTION", lesson_id="l1", node_id="n1")

    # Mock next step from QUESTION -> EVALUATE
    mock_question = {
        "node_id": "n1",
        "question_text": "Resumed Question: What is kinetic energy?",
        "type": "short_answer",
        "options": [],
        "expected_concept": "Kinetic Energy"
    }

    ai_mock.process_next_step.side_effect = [
        (TeacherState.EVALUATE, mock_question),
        (TeacherState.ADAPT, {"node_id": "n1", "correct": True, "partial_credit": 0.0, "misconception_tag": None, "confidence": 1.0, "feedback_text": "Correct"}),
        (TeacherState.DONE, {"action": "ALLOW", "target_node_id": "n1", "reason": "Good"}),
        (TeacherState.DONE, {"lesson_id": "l1", "score_pct": 100.0, "strong_areas": [], "weak_areas": [], "recommended_next": [], "narrative_feedback": "Perfect"})
    ]

    # Connect to WebSocket — should resume directly from QUESTION!
    with client.websocket_connect(f"/api/v1/sessions/{session_id}/live?token={token}") as ws:
        q = ws.receive_json()
        assert q["event_type"] == "interaction_event"
        assert "Resumed Question" in q["payload"]["question_text"]

        ws.send_json({
            "event_type": "student_response",
            "payload": {"node_id": "n1", "raw_answer": "0.5 * m * v^2", "response_type": "text", "response_time_sec": 1.5}
        })

        ev = ws.receive_json()
        assert ev["event_type"] == "evaluation_result"

        ad = ws.receive_json()
        assert ad["event_type"] == "adaptation_decision"
