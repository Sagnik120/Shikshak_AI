from typing import Optional, Dict
from modules.backend.src.persistence.base import SessionRepository

class InMemorySessionRepository(SessionRepository):
    def __init__(self):
        self._sessions: Dict[str, dict] = {}
        
    def create_session(self, session_id: str, token: str) -> None:
        self._sessions[session_id] = {
            "token": token,
            "topic": None,
            "constraints": None
        }
        
    def get_session_token(self, session_id: str) -> Optional[str]:
        session = self._sessions.get(session_id)
        if session:
            return session["token"]
        return None
        
    def save_topic(self, session_id: str, topic: str, constraints: dict) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["topic"] = topic
            self._sessions[session_id]["constraints"] = constraints
            
    def get_topic_and_constraints(self, session_id: str) -> Optional[tuple]:
        session = self._sessions.get(session_id)
        if session and session.get("topic"):
            return (session["topic"], session["constraints"])
        return None

# Singleton instance for MVP
session_repo = InMemorySessionRepository()
