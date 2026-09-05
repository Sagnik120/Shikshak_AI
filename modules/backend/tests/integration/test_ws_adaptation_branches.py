import pytest
from unittest.mock import Mock
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState


def test_ws_adaptation_modify_branch(client, mock_ai_service):
    """Verifies that an adaptation decision of MODIFY loops back to EXPLAIN."""
    ai_mock, avatar_mock = mock_ai_service

    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]

    mock_segment = {
        "node_id": "n1",
        "script_text": "First explanation.",
        "language": "en",
        "visual_spec": {"type": "image", "content": ""},
        "avatar_cue": "neutral"
    }
    mock_modified_segment = {
        "node_id": "n1",
        "script_text": "Simplified explanation using an analogy.",
        "language": "en",
        "visual_spec": {"type": "image", "content": ""},
        "avatar_cue": "encouraging"
    }

    # Setup side_effect sequence:
    # 1. EXPLAIN -> DEMONSTRATE
    # 2. DEMONSTRATE -> QUESTION
    # 3. QUESTION -> EVALUATE
    # 4. EVALUATE -> ADAPT (decision is MODIFY)
    # 5. ADAPT -> EXPLAIN (re-explain!)
    # 6. DEMONSTRATE -> DONE (finish)
    # 7. DONE -> report
    ai_mock.process_next_step.side_effect = [
        (TeacherState.DEMONSTRATE, mock_segment),
        (TeacherState.QUESTION, {"job_id": "job1"}),
        (TeacherState.EVALUATE, {"node_id": "n1", "question_text": "Q1?", "type": "short_answer", "options": [], "expected_concept": "C"}),
        (TeacherState.ADAPT, {"node_id": "n1", "correct": False, "partial_credit": 0.0, "misconception_tag": "SignError", "confidence": 0.9, "feedback_text": "Check sign"}),
        (TeacherState.EXPLAIN, {"action": "MODIFY", "target_node_id": "n1", "reason": "Explain with visual analogy"}),
        (TeacherState.DEMONSTRATE, mock_modified_segment),
        (TeacherState.DONE, {"job_id": "job2"}),
        (TeacherState.DONE, {"lesson_id": "l1", "score_pct": 50.0, "strong_areas": [], "weak_areas": [], "recommended_next": [], "narrative_feedback": "Keep practicing"})
    ]

    mock_status = Mock()
    mock_status.status = "done"
    mock_status.result = {"node_id": "n1", "video_url": "http://vid_modify", "duration_sec": 4.0, "captions_vtt_url": None}
    avatar_mock.get_status.return_value = mock_status

    with client.websocket_connect(f"/api/v1/sessions/{session_id}/live?token={token}") as ws:
        # First video + question
        v1 = ws.receive_json()
        assert v1["event_type"] == "video_segment"
        q1 = ws.receive_json()
        assert q1["event_type"] == "interaction_event"

        # Submit incorrect answer
        ws.send_json({
            "event_type": "student_response",
            "payload": {"node_id": "n1", "raw_answer": "wrong answer", "response_type": "text", "response_time_sec": 3.0}
        })

        # Evaluation result
        ev = ws.receive_json()
        assert ev["event_type"] == "evaluation_result"
        assert ev["payload"]["correct"] is False

        # Adaptation decision: MODIFY
        ad = ws.receive_json()
        assert ad["event_type"] == "adaptation_decision"
        assert ad["payload"]["action"] == "MODIFY"

        # Should loop back and produce modified video segment!
        v2 = ws.receive_json()
        assert v2["event_type"] == "video_segment"


def test_ws_adaptation_regenerate_branch(client, mock_ai_service):
    """Verifies that an adaptation decision of REGENERATE loops back to PLAN and emits lesson_plan_update."""
    ai_mock, avatar_mock = mock_ai_service

    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]

    mock_segment = {"node_id": "n1", "script_text": "First explanation.", "language": "en", "visual_spec": {"type": "image", "content": ""}, "avatar_cue": "neutral"}
    mock_new_plan = {
        "lesson_id": "l1_regen",
        "source": "topic",
        "constraints": {"level": "beginner", "language": "en", "time_budget_min": 10},
        "nodes": [{"node_id": "n1_easier", "concept": "Basics", "depth": "intro", "est_minutes": 2, "visual_type": "diagram", "checkpoint_question": False}]
    }

    ai_mock.process_next_step.side_effect = [
        (TeacherState.DEMONSTRATE, mock_segment),
        (TeacherState.QUESTION, {"job_id": "job1"}),
        (TeacherState.EVALUATE, {"node_id": "n1", "question_text": "Q1?", "type": "short_answer", "options": [], "expected_concept": "C"}),
        (TeacherState.ADAPT, {"node_id": "n1", "correct": False, "partial_credit": 0.0, "misconception_tag": "FoundationGap", "confidence": 1.0, "feedback_text": "Missing prerequisite"}),
        (TeacherState.PLAN, {"action": "REGENERATE", "target_node_id": "n1", "reason": "Regenerate curriculum from foundational level"}),
        (TeacherState.EXPLAIN, mock_new_plan),  # PLAN step produces updated plan
        (TeacherState.DEMONSTRATE, mock_segment),
        (TeacherState.DONE, {"job_id": "job2"}),
        (TeacherState.DONE, {"lesson_id": "l1", "score_pct": 60.0, "strong_areas": [], "weak_areas": [], "recommended_next": [], "narrative_feedback": "Review basics"})
    ]

    mock_status = Mock()
    mock_status.status = "done"
    mock_status.result = {"node_id": "n1", "video_url": "http://vid_regen", "duration_sec": 3.0, "captions_vtt_url": None}
    avatar_mock.get_status.return_value = mock_status

    with client.websocket_connect(f"/api/v1/sessions/{session_id}/live?token={token}") as ws:
        v1 = ws.receive_json()
        assert v1["event_type"] == "video_segment"
        q1 = ws.receive_json()
        assert q1["event_type"] == "interaction_event"

        ws.send_json({
            "event_type": "student_response",
            "payload": {"node_id": "n1", "raw_answer": "I don't know", "response_type": "text", "response_time_sec": 1.0}
        })

        ev = ws.receive_json()
        assert ev["event_type"] == "evaluation_result"

        ad = ws.receive_json()
        assert ad["event_type"] == "adaptation_decision"
        assert ad["payload"]["action"] == "REGENERATE"

        # Check for lesson_plan_update event emitted by PLAN step
        lpu = ws.receive_json()
        assert lpu["event_type"] == "lesson_plan_update"
        assert lpu["payload"]["lesson_id"] == "l1_regen"


def test_ws_adaptation_human_escalation(client, mock_ai_service):
    """Verifies that an adaptation decision of HUMAN emits human_escalation event."""
    ai_mock, avatar_mock = mock_ai_service

    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]

    mock_segment = {"node_id": "n1", "script_text": "First explanation.", "language": "en", "visual_spec": {"type": "image", "content": ""}, "avatar_cue": "neutral"}

    ai_mock.process_next_step.side_effect = [
        (TeacherState.DEMONSTRATE, mock_segment),
        (TeacherState.QUESTION, {"job_id": "job1"}),
        (TeacherState.EVALUATE, {"node_id": "n1", "question_text": "Q1?", "type": "short_answer", "options": [], "expected_concept": "C"}),
        (TeacherState.ADAPT, {"node_id": "n1", "correct": False, "partial_credit": 0.0, "misconception_tag": "PersistentConfusion", "confidence": 1.0, "feedback_text": "Stuck"}),
        (TeacherState.HUMAN_ESCALATION, {"action": "HUMAN", "target_node_id": "n1", "reason": "Requires human teacher assistance"})
    ]

    mock_status = Mock()
    mock_status.status = "done"
    mock_status.result = {"node_id": "n1", "video_url": "http://vid", "duration_sec": 2.0, "captions_vtt_url": None}
    avatar_mock.get_status.return_value = mock_status

    with client.websocket_connect(f"/api/v1/sessions/{session_id}/live?token={token}") as ws:
        v1 = ws.receive_json()
        q1 = ws.receive_json()

        ws.send_json({
            "event_type": "student_response",
            "payload": {"node_id": "n1", "raw_answer": "gibberish", "response_type": "text", "response_time_sec": 1.0}
        })

        ev = ws.receive_json()
        ad = ws.receive_json()
        assert ad["payload"]["action"] == "HUMAN"

        he = ws.receive_json()
        assert he["event_type"] == "human_escalation"
