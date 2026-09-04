import logging
from typing import Any, Dict, Optional
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState

logger = logging.getLogger(__name__)

def log_transition(
    session_id: str,
    from_state: TeacherState,
    to_state: TeacherState,
    reason: str,
    context_data: Optional[Dict[str, Any]] = None
) -> dict:
    """
    Structured logger that feeds the right-panel audit log.
    """
    log_entry = {
        "session_id": session_id,
        "transition": f"{from_state.name} -> {to_state.name}",
        "reason": reason,
        "context": context_data or {}
    }
    logger.info(f"FSM Transition: {log_entry}")
    return log_entry
