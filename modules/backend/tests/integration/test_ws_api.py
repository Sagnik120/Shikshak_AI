import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from modules.backend.src.persistence.in_memory import session_repo
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState

def test_ws_authentication_failure(client):
    with client.websocket_connect("/api/v1/sessions/bad_id/live?token=bad_token") as websocket:
        data = websocket.receive_json()
        assert data["event_type"] == "error"
        assert data["error"] == "Unauthorized"

def test_ws_happy_path(client, mock_ai_service):
    ai_mock, avatar_mock = mock_ai_service
    
    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]
    
    # Setup WS loop mocked behavior
    # Iteration 1: EXPLAIN -> DEMONSTRATE -> QUESTION (yields video_segment, then interaction_event)
    mock_segment = {"node_id": "n1", "script_text": "Hello", "language": "en", "visual_spec": {"type": "image", "content": ""}, "avatar_cue": "neutral"}
    mock_job_id = "job1"
    
    # Return sequence for driver.step inside the WS loop:
    # 1. EXPLAIN step -> returns DEMONSTRATE, segment
    # 2. DEMONSTRATE step -> returns QUESTION, {"job_id": job_id}
    # 3. QUESTION step -> returns EVALUATE, InteractionEvent
    # 4. EVALUATE step -> returns ADAPT, EvaluationResult
    # 5. ADAPT step -> returns DONE, AdaptationDecision
    # 6. DONE step -> returns DONE, AssessmentReport
    ai_mock.process_next_step.side_effect = [
        (TeacherState.DEMONSTRATE, mock_segment),
        (TeacherState.QUESTION, {"job_id": mock_job_id}),
        (TeacherState.EVALUATE, {"node_id": "n1", "question_text": "What?", "type": "short_answer", "options": [], "expected_concept": "C"}),
        (TeacherState.ADAPT, {"node_id": "n1", "correct": True, "partial_credit": 0.0, "misconception_tag": None, "confidence": 1.0, "feedback_text": "Good"}),
        (TeacherState.DONE, {"action": "ALLOW", "target_node_id": "n1", "reason": "Correct"}),
        (TeacherState.DONE, {"lesson_id": "l1", "score_pct": 100.0, "strong_areas": [], "weak_areas": [], "recommended_next": [], "narrative_feedback": "A"})
    ]
    
    # Avatar voice mock
    mock_status = Mock()
    mock_status.status = "done"
    mock_status.result = {"node_id": "n1", "video_url": "http://vid", "duration_sec": 5.0, "captions_vtt_url": None}
    avatar_mock.get_status.return_value = mock_status
    
    with client.websocket_connect(f"/api/v1/sessions/{session_id}/live?token={token}") as websocket:
        # Expecting video segment first
        vid_data = websocket.receive_json()
        assert vid_data["event_type"] == "video_segment"
        assert vid_data["payload"]["video_url"] == "http://vid"
        
        # Then interaction event
        q_data = websocket.receive_json()
        assert q_data["event_type"] == "interaction_event"
        assert q_data["payload"]["question_text"] == "What?"
        
        # Send student response
        websocket.send_json({
            "event_type": "student_response",
            "payload": {"node_id": "n1", "raw_answer": "ans", "response_type": "text", "response_time_sec": 1.0}
        })
        
        # Receive evaluation result
        e_data = websocket.receive_json()
        assert e_data["event_type"] == "evaluation_result"
        assert e_data["payload"]["correct"] is True
        
        # Receive adaptation decision
        a_data = websocket.receive_json()
        assert a_data["event_type"] == "adaptation_decision"
        assert a_data["payload"]["action"] == "ALLOW"
        
        # Finally report
        rep_data = websocket.receive_json()
        assert rep_data["event_type"] == "assessment_report"
        assert rep_data["payload"]["score_pct"] == 100.0
