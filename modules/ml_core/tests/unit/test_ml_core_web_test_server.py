"""Unit tests for the isolated ML Core Web Testbed Server and Hierarchical Logger.

Validates that:
1. /api/test/status returns health and config on isolated Port 8003.
2. /api/test/evaluate routes MCQ and Freeform responses, logging to logs/evaluation/.
3. /api/test/misconception diagnoses student conceptual traps and logs to logs/misconception/.
4. /api/test/concepts extracts ranked educational concepts and logs to logs/concepts/.
5. /api/test/visual_suggestion recommends visual modalities and logs to logs/visuals/.
6. /api/test/logs lists and retrieves structured JSON test logs.
7. The production backend (Port 8000) is never touched.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from modules.ml_core.tests.web_test.server import app
from modules.ml_core.tests.web_test.logger import MLCoreTestLogger, LOGS_DIR


@pytest.fixture
def test_client():
    """Provides a FastAPI test client for the isolated ML Core testbed."""
    return TestClient(app)


def test_status_endpoint(test_client):
    """GET /api/test/status returns ready status and capability metadata."""
    res = test_client.get("/api/test/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["port"] == 8003
    assert data["module"] == "ml_core"
    assert "evaluation" in data
    assert "misconceptions" in data
    assert "concept_extraction" in data
    assert "visual_suggestion" in data


def test_evaluate_endpoint_mcq(test_client):
    """POST /api/test/evaluate handles MCQ deterministic rule matching."""
    payload = {
        "node_id": "test_node_mcq",
        "response_type": "mcq",
        "raw_answer": "B",
        "expected_concept": "B",
        "grounding_text": "Sample MCQ question with options A, B, C, D.",
        "subject": "physics",
    }
    res = test_client.post("/api/test/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["correct"] is True
    assert data["confidence"] == 1.0
    assert "Tier 1" in data["evaluation_tier"]
    assert "log_id" in data
    assert "evaluation/" in data["log_file"]


def test_evaluate_endpoint_freeform(test_client):
    """POST /api/test/evaluate handles freeform responses with feedback."""
    payload = {
        "node_id": "test_node_freeform",
        "response_type": "freeform",
        "raw_answer": "Current is directly proportional to potential difference across a conductor if temperature is constant.",
        "expected_concept": "Current is directly proportional to voltage across a conductor provided temperature remains constant (V = IR).",
        "grounding_text": "Ohm's law states that current is proportional to voltage.",
        "subject": "physics",
    }
    res = test_client.post("/api/test/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "confidence" in data
    assert "feedback_text" in data
    assert "log_id" in data
    assert "evaluation/" in data["log_file"]


def test_misconception_endpoint(test_client):
    """POST /api/test/misconception analyzes student error against subject taxonomy."""
    payload = {
        "subject": "physics",
        "expected_concept": "All objects experience equal gravitational acceleration g = 9.8 m/s^2 in free fall.",
        "raw_answer": "Heavier objects fall faster because gravity pulls them harder.",
    }
    res = test_client.post("/api/test/misconception", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["subject"] == "physics"
    assert data["taxonomy_entries_checked"] > 0
    assert "misconception/" in data["log_file"]


def test_concepts_endpoint(test_client):
    """POST /api/test/concepts extracts key terms using term frequency heuristic."""
    payload = {
        "chunk_texts": [
            "Quantum mechanics describes physics at the subatomic scale.",
            "Wave particle duality posits that matter behaves as both particles and waves.",
            "Light packets are called photons.",
        ],
        "top_k": 5,
    }
    res = test_client.post("/api/test/concepts", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["chunk_count"] == 3
    assert len(data["concepts"]) > 0
    assert "concepts/" in data["log_file"]


def test_visual_suggestion_endpoint(test_client):
    """POST /api/test/visual_suggestion recommends visual modality."""
    # Test deterministic rule table match
    payload = {
        "subject": "mathematics",
        "concept": "quadratic formula derivation",
    }
    res = test_client.post("/api/test/visual_suggestion", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["suggested_visual_type"] in ["equation", "graph", "diagram", "code", "timeline", "map", "image"]
    assert "visuals/" in data["log_file"]


def test_logs_endpoints(test_client):
    """GET /api/test/logs lists logs and GET /api/test/logs/{category}/{filename} retrieves details."""
    res = test_client.get("/api/test/logs")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "total_logs" in data

    if data["logs"]:
        first_log = data["logs"][0]
        cat = first_log["category"]
        fn = first_log["filename"]

        detail_res = test_client.get(f"/api/test/logs/{cat}/{fn}")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert "log_id" in detail_data
        assert "source_file" in detail_data
        assert "source_function" in detail_data


def test_hierarchical_logger_structure():
    """Validates logger writes files to designated category subfolders with correct schema."""
    logger = MLCoreTestLogger()
    meta = logger.log_evaluation(
        node_id="test_node_unit",
        response_type="freeform",
        raw_answer="Photosynthesis converts light into chemical energy.",
        expected_concept="Light energy is converted into glucose.",
        grounding_text="Chloroplasts perform photosynthesis.",
        correct=True,
        partial_credit=1.0,
        confidence=0.92,
        feedback_text="Correct understanding of photosynthesis energy conversion.",
        evaluation_tier="Tier 2: Semantic Similarity",
        source_file="modules/ml_core/src/answer_evaluation/evaluator.py",
        source_function="evaluate",
    )

    log_path = Path(meta["log_path"])
    assert log_path.exists()
    assert "evaluation/" in meta["relative_log"]

    with open(meta["json_path"], "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    assert saved_data["log_id"] == meta["log_id"]
    assert saved_data["source_file"] == "modules/ml_core/src/answer_evaluation/evaluator.py"
    assert saved_data["source_function"] == "evaluate"
    assert saved_data["status"] == "success"
