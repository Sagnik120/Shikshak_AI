from typing import Any, Dict
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.backend.src.integrations.container import services

ai_service = services["ai_service"]

class SessionDriver:
    """State Machine Driver acting as a thin relay to AIOperationService."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        # Initialize session in orchestrator if not exists
        try:
            self.session = ai_service.get_session(session_id)
        except KeyError:
            self.session = ai_service.init_session(session_id)

    def step(self, current_state: TeacherState, inputs: Dict[str, Any]):
        """Advance the FSM one step using AIOperationService."""
        return ai_service.process_next_step(self.session_id, current_state, inputs)
