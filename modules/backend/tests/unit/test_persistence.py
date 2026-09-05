import pytest
import os
from modules.backend.src.persistence.in_memory import (
    InMemorySessionRepository,
    InMemoryLearnerProfileRepository,
    InMemoryAssessmentReportRepository,
    InMemoryUploadedDocumentRepository,
)
from modules.backend.src.persistence.storage import LocalStorageAdapter
from modules.backend.src.schemas.contract import LearnerProfile, AssessmentReport


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


def test_session_document_context_and_checkpoint():
    repo = InMemorySessionRepository()
    repo.create_session("session1", "token123")

    # Document context
    repo.save_document_context("session1", "doc_abc", {"level": "advanced"})
    doc_data = repo.get_document_context("session1")
    assert doc_data is not None
    assert doc_data[0] == "doc_abc"
    assert doc_data[1]["level"] == "advanced"

    # State checkpointing
    repo.save_state("session1", "QUESTION", lesson_id="l1", node_id="n1")
    state_data = repo.get_state("session1")
    assert state_data["current_state"] == "QUESTION"
    assert state_data["lesson_id"] == "l1"
    assert state_data["node_id"] == "n1"


def test_learner_profile_repository():
    repo = InMemoryLearnerProfileRepository()
    profile = LearnerProfile(
        learner_id="lrn_1",
        history=[],
        strong_concepts=["Physics"],
        weak_concepts=[],
        current_learning_path=[],
        preferred_language="hi",
        preferred_level="beginner"
    )
    repo.save_profile(profile)
    retrieved = repo.get_profile("lrn_1")
    assert retrieved is not None
    assert retrieved.preferred_language == "hi"
    assert repo.get_profile("unknown") is None


def test_assessment_report_repository():
    repo = InMemoryAssessmentReportRepository()
    report = AssessmentReport(
        lesson_id="les_1",
        score_pct=92.0,
        strong_areas=["A"],
        weak_areas=["B"],
        recommended_next=["C"],
        narrative_feedback="Well done"
    )
    repo.save_report("lrn_1", report)
    retrieved = repo.get_report("lrn_1", "les_1")
    assert retrieved is not None
    assert retrieved.score_pct == 92.0
    assert repo.get_report("lrn_1", "unknown") is None


def test_uploaded_document_repository():
    repo = InMemoryUploadedDocumentRepository()
    repo.create_document("doc_1", "notes.pdf", "application/pdf", "/tmp/notes.pdf")

    doc = repo.get_document("doc_1")
    assert doc is not None
    assert doc["status"] == "ingesting"

    repo.update_status("doc_1", "ready")
    assert repo.get_document("doc_1")["status"] == "ready"

    repo.update_status("doc_1", "failed", error="Corrupt PDF")
    assert repo.get_document("doc_1")["status"] == "failed"
    assert repo.get_document("doc_1")["error"] == "Corrupt PDF"


def test_storage_adapter(tmp_path):
    storage = LocalStorageAdapter(base_dir=str(tmp_path))
    content = b"Binary video or PDF chunk bytes"

    # Put
    path = storage.put("sample.bin", content)
    assert os.path.exists(path)

    # Get
    retrieved = storage.get("sample.bin")
    assert retrieved == content

    # Delete
    assert storage.delete("sample.bin") is True
    assert storage.get("sample.bin") is None
    assert storage.delete("sample.bin") is False
