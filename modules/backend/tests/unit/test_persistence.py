import pytest
from modules.backend.src.persistence.in_memory import InMemorySessionRepository

def test_create_and_retrieve_session():
    repo = InMemorySessionRepository()
    repo.create_session("session1", "token123")
    assert repo.get_session_token("session1") == "token123"
    assert repo.get_session_token("unknown") is None

def test_save_and_get_topic():
    repo = InMemorySessionRepository()
    repo.create_session("session1", "token123")
    
    constraints = {"level": "beginner", "language": "en", "time_budget_min": 10}
    repo.save_topic("session1", "Photosynthesis", constraints)
    
    data = repo.get_topic_and_constraints("session1")
    assert data is not None
    topic, retrieved_constraints = data
    assert topic == "Photosynthesis"
    assert retrieved_constraints["level"] == "beginner"

def test_get_topic_no_topic():
    repo = InMemorySessionRepository()
    repo.create_session("session1", "token123")
    assert repo.get_topic_and_constraints("session1") is None
