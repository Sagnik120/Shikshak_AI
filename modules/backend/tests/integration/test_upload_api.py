import io
import json
import pytest
from unittest.mock import Mock, patch
from modules.backend.src.persistence.in_memory import session_repo, document_repo
from modules.backend.src.schemas.contract import ParsedDocument, ChunkInfo, DocumentStructure
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState


def test_upload_document_success(client):
    """Test successful multipart document upload and RAG integration."""
    # 1. Create session
    resp = client.post("/api/v1/sessions")
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Mock RAGService.ingest_document
    mock_parsed_doc = ParsedDocument(
        document_id="doc_test_123",
        source_lang="en",
        chunks=[
            ChunkInfo(
                chunk_id="c1",
                text="Thermodynamics is the study of heat.",
                section_title="Chapter 1",
                page_or_slide=1,
                embedding_ref="emb_1"
            )
        ],
        detected_structure=DocumentStructure(
            chapters=["Chapter 1: Thermodynamics"],
            key_terms=["Heat", "Entropy"]
        )
    )

    with patch("modules.backend.src.api.rest.services") as mock_services:
        rag_mock = Mock()
        rag_mock.ingest_document.return_value = mock_parsed_doc
        mock_services.__getitem__.side_effect = lambda k: rag_mock if k == "rag_service" else Mock()

        file_content = b"%PDF-1.4 Mock PDF Content For Testing"
        files = {"file": ("test_thermo.pdf", io.BytesIO(file_content), "application/pdf")}
        data = {"constraints": json.dumps({"level": "intermediate", "language": "en", "time_budget_min": 20})}

        upload_resp = client.post(
            f"/api/v1/sessions/{session_id}/upload",
            files=files,
            data=data,
            headers=headers
        )

        assert upload_resp.status_code == 200
        result = upload_resp.json()
        assert result["status"] == "ready"
        assert "document_id" in result
        assert result["detected_structure"]["chapters"] == ["Chapter 1: Thermodynamics"]

        # Verify document metadata persistence
        doc_id = result["document_id"]
        doc_meta = document_repo.get_document(doc_id)
        assert doc_meta is not None
        assert doc_meta["status"] == "ready"
        assert doc_meta["filename"] == "test_thermo.pdf"


def test_upload_document_unauthorized(client):
    """Verifies that upload without valid bearer token is rejected with 401."""
    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]

    files = {"file": ("test.pdf", io.BytesIO(b"dummy bytes"), "application/pdf")}
    upload_resp = client.post(
        f"/api/v1/sessions/{session_id}/upload",
        files=files,
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert upload_resp.status_code == 401


def test_upload_empty_file_rejected(client):
    """Verifies that an empty file payload is rejected with 422."""
    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]

    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    upload_resp = client.post(
        f"/api/v1/sessions/{session_id}/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert upload_resp.status_code == 422


def test_document_grounded_plan_generation(client, mock_ai_service):
    """Verifies that planning after document upload passes document_id to the Orchestrator."""
    ai_mock, avatar_mock = mock_ai_service

    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["session_id"]
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate uploaded document associated with session
    session_repo.save_document_context(
        session_id=session_id,
        document_id="doc_bio_456",
        constraints={"level": "advanced", "language": "en", "time_budget_min": 30}
    )

    mock_plan = {
        "lesson_id": "l_doc",
        "source": "document",
        "constraints": {"level": "advanced", "language": "en", "time_budget_min": 30},
        "nodes": [{"node_id": "n1", "concept": "Cell Biology", "depth": "advanced", "est_minutes": 5, "visual_type": "diagram", "checkpoint_question": True}]
    }

    ai_mock.process_next_step.side_effect = [
        (TeacherState.PLAN, None),
        (TeacherState.EXPLAIN, mock_plan)
    ]

    plan_resp = client.post(f"/api/v1/sessions/{session_id}/plan", headers=headers)
    assert plan_resp.status_code == 200
    assert plan_resp.json()["source"] == "document"

    # Verify that UNDERSTAND step received document_id="doc_bio_456"
    first_call_args = ai_mock.process_next_step.call_args_list[0]
    inputs = first_call_args[0][2]
    assert inputs.get("document_id") == "doc_bio_456"
