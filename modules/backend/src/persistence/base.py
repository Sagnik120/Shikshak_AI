from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from modules.backend.src.schemas.contract import LearnerProfile, AssessmentReport


class SessionRepository(ABC):
    """Repository for managing session authentication, configuration, and state."""

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
    def get_topic_and_constraints(self, session_id: str) -> Optional[Tuple[str, dict]]:
        pass

    @abstractmethod
    def save_document_context(self, session_id: str, document_id: str, constraints: Optional[dict] = None) -> None:
        pass

    @abstractmethod
    def get_document_context(self, session_id: str) -> Optional[Tuple[str, Optional[dict]]]:
        pass

    @abstractmethod
    def save_state(self, session_id: str, current_state: str, lesson_id: Optional[str] = None, node_id: Optional[str] = None) -> None:
        """Persist state machine checkpoint for reconnection/resumption."""
        pass

    @abstractmethod
    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve state machine checkpoint."""
        pass


class LearnerProfileRepository(ABC):
    """Repository for storing and retrieving learner profiles (Contract §13)."""

    @abstractmethod
    def get_profile(self, learner_id: str) -> Optional[LearnerProfile]:
        pass

    @abstractmethod
    def save_profile(self, profile: LearnerProfile) -> None:
        pass


class AssessmentReportRepository(ABC):
    """Repository for storing and retrieving lesson assessment reports (Contract §12)."""

    @abstractmethod
    def get_report(self, learner_id: str, lesson_id: str) -> Optional[AssessmentReport]:
        pass

    @abstractmethod
    def save_report(self, learner_id: str, report: AssessmentReport) -> None:
        pass


class UploadedDocumentRepository(ABC):
    """Repository for tracking uploaded document metadata and ingestion status."""

    @abstractmethod
    def create_document(self, document_id: str, filename: str, mime_type: str, file_path: str) -> None:
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update_status(self, document_id: str, status: str, error: Optional[str] = None) -> None:
        pass
