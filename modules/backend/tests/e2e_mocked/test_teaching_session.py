import pytest
from unittest.mock import Mock, patch
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState

def test_full_mocked_teaching_journey(client, mock_ai_service):
    """
    E2E mocked session covering the full P0 REST + WS integration path.
    """
    ai_mock, avatar_mock = mock_ai_service
    
    # 1. Create Session
    resp = client.post("/api/v1/sessions")
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Topic Submission
    topic_payload = {
        "session_id": session_id,
        "topic": "Photosynthesis",
        "constraints": {"level": "beginner", "language": "en", "time_budget_min": 10}
    }
    client.post(f"/api/v1/sessions/{session_id}/topic", json=topic_payload, headers=headers)
    
    # 3. Lesson Planning
    mock_plan = {
        "lesson_id": "l1", "source": "topic",
        "constraints": {"level": "beginner", "language": "en", "time_budget_min": 10},
        "nodes": [{"node_id": "n1", "concept": "Intro", "depth": "intro", "est_minutes": 2, "visual_type": "image", "checkpoint_question": True}]
    }
    ai_mock.process_next_step.side_effect = [
        (TeacherState.PLAN, None),
        (TeacherState.EXPLAIN, mock_plan)
    ]
    
    plan_resp = client.post(f"/api/v1/sessions/{session_id}/plan", headers=headers)
    assert plan_resp.status_code == 200
    assert plan_resp.json()["nodes"][0]["node_id"] == "n1"
    
    # Reset mock for WS loop
    ai_mock.process_next_step.reset_mock()
    
    # 4. WebSocket Flow
    mock_segment = {"node_id": "n1", "script_text": "Sunlight is key.", "language": "en", "visual_spec": {"type": "image", "content": ""}, "avatar_cue": "neutral"}
    ai_mock.process_next_step.side_effect = [
        (TeacherState.DEMONSTRATE, mock_segment),
        (TeacherState.QUESTION, {"job_id": "job1"}),
        (TeacherState.EVALUATE, {"node_id": "n1", "question_text": "Q1", "type": "short_answer", "options": [], "expected_concept": "C1"}),
        (TeacherState.ADAPT, {"node_id": "n1", "correct": True, "partial_credit": 0.0, "misconception_tag": None, "confidence": 1.0, "feedback_text": "Great"}),
        (TeacherState.DONE, {"action": "ALLOW", "target_node_id": "n1", "reason": "Correct"}),
        (TeacherState.DONE, {"lesson_id": "l1", "score_pct": 100.0, "strong_areas": [], "weak_areas": [], "recommended_next": [], "narrative_feedback": "A"})
    ]
    
    mock_status = Mock()
    mock_status.status = "done"
    mock_status.result = {"node_id": "n1", "video_url": "url", "duration_sec": 5.0, "captions_vtt_url": None}
    avatar_mock.get_status.return_value = mock_status
    
    with client.websocket_connect(f"/api/v1/sessions/{session_id}/live?token={token}") as ws:
        vid = ws.receive_json()
        assert vid["event_type"] == "video_segment"
        
        q = ws.receive_json()
        assert q["event_type"] == "interaction_event"
        
        ws.send_json({
            "event_type": "student_response",
            "payload": {"node_id": "n1", "raw_answer": "ans", "response_type": "text", "response_time_sec": 2.0}
        })
        
        ev = ws.receive_json()
        assert ev["event_type"] == "evaluation_result"
        
        ad = ws.receive_json()
        assert ad["event_type"] == "adaptation_decision"
        
        rep = ws.receive_json()
        assert rep["event_type"] == "assessment_report"
