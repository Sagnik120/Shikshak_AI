import pytest
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.ai_agent_orchestration.src.state_machine.transitions import is_valid_transition, VALID_TRANSITIONS
from modules.ai_agent_orchestration.src.logging_utils import log_transition

def test_is_valid_transition():
    assert is_valid_transition(TeacherState.UNDERSTAND, TeacherState.PLAN) is True
    assert is_valid_transition(TeacherState.PLAN, TeacherState.EXPLAIN) is True
    assert is_valid_transition(TeacherState.EXPLAIN, TeacherState.DEMONSTRATE) is True
    assert is_valid_transition(TeacherState.DEMONSTRATE, TeacherState.QUESTION) is True
    assert is_valid_transition(TeacherState.DEMONSTRATE, TeacherState.CONTINUE) is True
    assert is_valid_transition(TeacherState.QUESTION, TeacherState.EVALUATE) is True
    assert is_valid_transition(TeacherState.EVALUATE, TeacherState.ADAPT) is True
    assert is_valid_transition(TeacherState.ADAPT, TeacherState.EXPLAIN) is True # MODIFY
    assert is_valid_transition(TeacherState.ADAPT, TeacherState.PLAN) is True # REGENERATE
    assert is_valid_transition(TeacherState.ADAPT, TeacherState.HUMAN_ESCALATION) is True # HUMAN
    assert is_valid_transition(TeacherState.ADAPT, TeacherState.CONTINUE) is True # ALLOW
    assert is_valid_transition(TeacherState.CONTINUE, TeacherState.DONE) is True
    
def test_invalid_transition():
    assert is_valid_transition(TeacherState.PLAN, TeacherState.DONE) is False
    assert is_valid_transition(TeacherState.DONE, TeacherState.PLAN) is False

def test_logging_utils():
    log = log_transition("session_123", TeacherState.PLAN, TeacherState.EXPLAIN, "Testing", {"key": "value"})
    assert log["session_id"] == "session_123"
    assert log["transition"] == "PLAN -> EXPLAIN"
    assert log["reason"] == "Testing"
    assert log["context"]["key"] == "value"
