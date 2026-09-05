from typing import Optional, Dict, Any, Tuple
from modules.backend.src.persistence.base import (
    SessionRepository,
    LearnerProfileRepository,
    AssessmentReportRepository,
    UploadedDocumentRepository,
)
from modules.backend.src.persistence.storage import LocalStorageAdapter
from modules.backend.src.schemas.contract import LearnerProfile, AssessmentReport


class InMemorySessionRepository(SessionRepository):
    def __init__(self):
        self._sessions: Dict[str, dict] = {}

    def create_session(self, session_id: str, token: str) -> None:
        self._sessions[session_id] = {
            "token": token,
            "topic": None,
            "constraints": None,
            "document_id": None,
            "current_state": "CREATED",
            "lesson_id": None,
            "node_id": None,
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

    def get_topic_and_constraints(self, session_id: str) -> Optional[Tuple[str, dict]]:
        session = self._sessions.get(session_id)
        if session and session.get("topic"):
            return (session["topic"], session["constraints"])
        return None

    def save_document_context(self, session_id: str, document_id: str, constraints: Optional[dict] = None) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["document_id"] = document_id
            if constraints:
                self._sessions[session_id]["constraints"] = constraints

    def get_document_context(self, session_id: str) -> Optional[Tuple[str, Optional[dict]]]:
        session = self._sessions.get(session_id)
        if session and session.get("document_id"):
            return (session["document_id"], session.get("constraints"))
        return None

    def save_state(self, session_id: str, current_state: str, lesson_id: Optional[str] = None, node_id: Optional[str] = None) -> None:
        if session_id in self._sessions:
            self._sessions[session_id]["current_state"] = current_state
            if lesson_id is not None:
                self._sessions[session_id]["lesson_id"] = lesson_id
            if node_id is not None:
                self._sessions[session_id]["node_id"] = node_id

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session:
            return {
                "current_state": session.get("current_state", "CREATED"),
                "lesson_id": session.get("lesson_id"),
                "node_id": session.get("node_id"),
            }
        return None


class InMemoryLearnerProfileRepository(LearnerProfileRepository):
    def __init__(self):
        self._profiles: Dict[str, LearnerProfile] = {}

    def get_profile(self, learner_id: str) -> Optional[LearnerProfile]:
        return self._profiles.get(learner_id)

    def save_profile(self, profile: LearnerProfile) -> None:
        self._profiles[profile.learner_id] = profile


class InMemoryAssessmentReportRepository(AssessmentReportRepository):
    def __init__(self):
        # (learner_id, lesson_id) -> AssessmentReport
        self._reports: Dict[Tuple[str, str], AssessmentReport] = {}

    def get_report(self, learner_id: str, lesson_id: str) -> Optional[AssessmentReport]:
        return self._reports.get((learner_id, lesson_id))

    def save_report(self, learner_id: str, report: AssessmentReport) -> None:
        self._reports[(learner_id, report.lesson_id)] = report


class InMemoryUploadedDocumentRepository(UploadedDocumentRepository):
    def __init__(self):
        self._docs: Dict[str, dict] = {}

    def create_document(self, document_id: str, filename: str, mime_type: str, file_path: str) -> None:
        self._docs[document_id] = {
            "document_id": document_id,
            "filename": filename,
            "mime_type": mime_type,
            "file_path": file_path,
            "status": "ingesting",
            "error": None,
        }

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        return self._docs.get(document_id)

    def update_status(self, document_id: str, status: str, error: Optional[str] = None) -> None:
        if document_id in self._docs:
            self._docs[document_id]["status"] = status
            self._docs[document_id]["error"] = error


# Global singleton instances for MVP
session_repo = InMemorySessionRepository()
learner_repo = InMemoryLearnerProfileRepository()
report_repo = InMemoryAssessmentReportRepository()
document_repo = InMemoryUploadedDocumentRepository()
storage_adapter = LocalStorageAdapter()
