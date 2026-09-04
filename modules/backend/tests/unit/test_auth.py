import pytest
from modules.backend.src.auth import generate_session_token, verify_token
from modules.backend.src.persistence.in_memory import InMemorySessionRepository

def test_generate_session_token():
    token = generate_session_token()
    assert isinstance(token, str)
    assert len(token) > 0

def test_verify_token():
    repo = InMemorySessionRepository()
    repo.create_session("session1", "token123")
    
    # Valid
    assert verify_token("session1", "token123", repo) is True
    
    # Invalid token
    assert verify_token("session1", "wrong", repo) is False
    
    # Unknown session
    assert verify_token("unknown", "token123", repo) is False
