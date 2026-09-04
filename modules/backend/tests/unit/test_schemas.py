import pytest
from pydantic import ValidationError
from modules.backend.src.schemas.contract import TopicRequest, InteractionEvent
from modules.backend.src.schemas.ws import WSMessage

def test_topic_request_validation():
    # Valid
    req = TopicRequest(
        session_id="123",
        topic="Math",
        constraints={"level": "beginner", "language": "en", "time_budget_min": 15}
    )
    assert req.topic == "Math"
    assert req.constraints.level == "beginner"

    # Invalid constraint enum
    with pytest.raises(ValidationError):
        TopicRequest(
            session_id="123",
            topic="Math",
            constraints={"level": "expert", "language": "en", "time_budget_min": 15} # expert is invalid
        )

def test_ws_message_validation():
    # Valid
    msg = WSMessage(event_type="interaction_event", payload={"node_id": "n1"})
    assert msg.event_type == "interaction_event"
    assert msg.payload["node_id"] == "n1"
    
    # Missing payload
    with pytest.raises(ValidationError):
        WSMessage(event_type="interaction_event")
