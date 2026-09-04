from abc import ABC, abstractmethod
from typing import Optional

class SessionRepository(ABC):
    @abstractmethod
    def create_session(self, session_id: str, token: str) -> None:
        pass
        
    @abstractmethod
    def get_session_token(self, session_id: str) -> Optional[str]:
        pass
        
    @abstractmethod
    def save_topic(self, session_id: str, topic: str, constraints: dict) -> None:
        pass
        
    @abstractmethod
    def get_topic_and_constraints(self, session_id: str) -> Optional[tuple]:
        pass
