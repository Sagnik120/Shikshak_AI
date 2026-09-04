import logging
from typing import Dict, Any, Tuple
from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.ai_agent_orchestration.src.state_machine.session_state import SessionState

logger = logging.getLogger(__name__)

class AIOperationService:
    """Public service entrypoint for AI Orchestration."""
    
    def __init__(self, orchestrator: TeacherOrchestrator):
        self.orchestrator = orchestrator
        self.sessions: Dict[str, SessionState] = {}
        
    def init_session(self, session_id: str) -> SessionState:
        session = SessionState(session_id=session_id)
        self.sessions[session_id] = session
        return session
        
    def get_session(self, session_id: str) -> SessionState:
        if session_id not in self.sessions:
            raise KeyError(f"Session {session_id} not found.")
        return self.sessions[session_id]
        
    def process_next_step(
        self,
        session_id: str,
        current_state: TeacherState,
        inputs: Dict[str, Any]
    ) -> Tuple[TeacherState, Any]:
        """
        Advance the session FSM by one step.
        """
        session = self.get_session(session_id)
        
        try:
            next_state, payload = self.orchestrator.step(current_state, session, inputs)
            return next_state, payload
        except Exception as e:
            logger.exception(f"FSM step failed for session {session_id} at {current_state}")
            raise
