"""Automated test suite verifying the isolated RAG web test server and structured logger."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from modules.rag.tests.web_test.server import app
from modules.rag.tests.web_test.logger import RAGTestLogger


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


def test_status_endpoint(client):
    """Ensure /api/test/status returns server metadata and seeded documents."""
    resp = client.get("/api/test/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["port"] == 8002
    assert "Untouched" in data["production_backend"]
    assert "cached_documents" in data
    assert len(data["cached_documents"]) >= 2  # Seeded physics & hindi samples


def test_parse_text_endpoint(client):
    """Ensure /api/test/parse correctly ingests raw text into Contract §4 ParsedDocument."""
    text_payload = """Chapter 1: Basics of Mechanical Motion
Motion is a change in position of an object over time. Motion is described in terms of displacement, distance, velocity, and speed."""
    resp = client.post(
        "/api/test/parse",
        data={
            "raw_text": text_payload,
            "filename": "test_motion.txt",
            "document_id": "doc_motion_test"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == "doc_motion_test"
    assert data["source_lang"] == "en"
    assert data["chunk_count"] >= 1
    assert "Motion" in data["key_terms"] or len(data["key_terms"]) > 0


def test_chunk_endpoint(client):
    """Ensure /api/test/chunk verifies token budgets and returns chunk structures."""
    resp = client.post(
        "/api/test/chunk",
        json={
            "text": "An electric circuit is a continuous and closed path of an electric current.",
            "target_tokens": 300,
            "max_tokens": 500,
            "overlap_pct": 0.15
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_chunks"] >= 1
    assert data["chunks"][0]["satisfies_budget"] is True


def test_embed_endpoint(client):
    """Ensure /api/test/embed generates dense and sparse outputs."""
    resp = client.post(
        "/api/test/embed",
        json={"texts": ["Electric potential difference is measured in volts."]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_texts"] == 1
    result = data["results"][0]
    assert result["dense_dimension"] > 0
    assert "dense_sample" in result
    assert isinstance(result["top_sparse_terms"], dict)


def test_retrieval_endpoint(client):
    """Ensure /api/test/retrieve returns ranked candidate chunks and handles topic-only mode."""
    # 1. Standard retrieval against seeded physics document
    resp = client.post(
        "/api/test/retrieve",
        json={
            "document_id": "doc_physics_ohm",
            "query_text": "What is Ohm's Law and the formula V=IR?",
            "top_k": 3
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == "doc_physics_ohm"
    assert data["candidate_count"] > 0
    assert data["has_sufficient_context"] is True

    # 2. Topic-Only Mode
    resp_topic = client.post(
        "/api/test/retrieve",
        json={
            "document_id": "topic_only",
            "query_text": "Teach me React hooks from the beginning"
        }
    )
    assert resp_topic.status_code == 200
    data_topic = resp_topic.json()
    assert data_topic["document_id"] is None
    assert data_topic["risk_level"] == "no_document_context"
    assert data_topic["candidate_count"] == 0


def test_grounding_valid_citation_audit(client):
    """Ensure valid citation passes hallucination audit."""
    resp = client.post(
        "/api/test/grounding",
        json={
            "document_id": "doc_physics_ohm",
            "query_text": "What is Ohm's Law?",
            "simulated_teacher_response": 'Ohm\'s Law relates voltage and current: V = I * R.\n\ngrounded_on: ["chunk_doc_physics_ohm_0001"]'
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "prompt_context" in data
    assert "citation_audit" in data
    # Notice: chunk_doc_physics_ohm_0001 is in candidate_chunk_ids
    audit = data["citation_audit"]
    assert "chunk_doc_physics_ohm_0001" in audit["cited_chunk_ids"]


def test_grounding_hallucination_detection(client):
    """Ensure citation of non-existent chunk ID triggers hallucination detection and flags source file."""
    resp = client.post(
        "/api/test/grounding",
        json={
            "document_id": "doc_physics_ohm",
            "query_text": "What is Ohm's Law?",
            "simulated_teacher_response": 'Ohm\'s Law explanation.\n\ngrounded_on: ["chunk_fake_hallucinated_9999"]'
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    audit = data["citation_audit"]
    assert audit["is_hallucinating"] is True
    assert "modules/rag/src/grounding/extractor.py" in audit["hallucination_source_file"]
    assert audit["hallucination_source_function"] == "parse_grounded_citations"
    assert "chunk_fake_hallucinated_9999" in audit["risk_signal"]


def test_logs_endpoint(client):
    """Ensure /api/test/logs retrieves structured diagnostic log manifests."""
    resp = client.get("/api/test/logs?category=all")
    assert resp.status_code == 200
    data = resp.json()
    assert "logs" in data
    assert len(data["logs"]) >= 1
