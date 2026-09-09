"""Unit tests for the isolated Avatar & Voice Web Testbed Server and Hierarchical Logger.

Validates that:
1. /api/test/status returns health and config on isolated port 8004.
2. /api/test/tts synthesizes speech and logs to logs/tts/ with file/function trace.
3. /api/test/avatar animates visemes and logs to logs/avatar/.
4. /api/test/visuals renders slide visual specs and logs to logs/visuals/.
5. /api/test/logs lists and retrieves structured JSON test logs.
6. The actual backend (Port 8000) is never touched.
"""

import pytest
from fastapi.testclient import TestClient

from modules.avatar_voice.tests.web_test.server import app
from modules.avatar_voice.tests.web_test.logger import AvatarVoiceTestLogger, LOGS_DIR


@pytest.fixture
def test_client():
    """Provides a FastAPI test client for the isolated testbed."""
    return TestClient(app)


def test_status_endpoint(test_client):
    """GET /api/test/status returns ready status and capability metadata."""
    res = test_client.get("/api/test/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["port"] == 8004
    assert "tts" in data
    assert "avatar" in data
    assert "visuals" in data
    assert "compositor" in data
    assert "en" in data["tts"]["supported_languages"]


def test_tts_endpoint_fallback(test_client):
    """POST /api/test/tts synthesizes speech and creates a structured log."""
    payload = {
        "text": "The fundamental theorem of calculus connects differentiation with integration.",
        "language": "en",
        "provider": "fallback",
        "avatar_cue": "emphasis",
    }
    res = test_client.post("/api/test/tts", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "audio_url" in data
    assert data["duration_sec"] > 0
    assert data["word_count"] > 0
    assert "log_id" in data
    assert "log_file" in data
    assert "tts/" in data["log_file"]


def test_avatar_endpoint(test_client):
    """POST /api/test/avatar generates viseme frames and creates a structured log."""
    payload = {
        "script_text": "Step one is expanding the quadratic expression.",
        "language": "en",
        "avatar_cue": "emphasis",
        "engine": "tier1",
    }
    res = test_client.post("/api/test/avatar", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["tier_used"] == "tier1_viseme"
    assert data["frame_count"] > 0
    assert data["fps"] == 24
    assert len(data["mouth_states_detected"]) > 0
    assert "avatar/" in data["log_file"]


def test_visuals_endpoint_equation(test_client):
    """POST /api/test/visuals renders LaTeX slide and progressive reveal steps."""
    payload = {
        "visual_type": "equation",
        "content": "E = mc^2",
        "steps": [
            "Step 1: Energy E is equivalent to mass m times the speed of light squared c^2.",
            "Step 2: Dimensional analysis confirms kg * (m/s)^2 = Joules.",
        ],
    }
    res = test_client.post("/api/test/visuals", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["visual_type"] == "equation"
    assert "primary_image_url" in data
    assert data["step_count"] == 2
    assert "visuals/" in data["log_file"]


def test_logs_endpoints(test_client):
    """GET /api/test/logs lists logs and GET /api/test/logs/{category}/{filename} retrieves details."""
    # List all logs
    res = test_client.get("/api/test/logs")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "total_logs" in data

    if data["logs"]:
        first_log = data["logs"][0]
        cat = first_log["category"]
        fn = first_log["filename"]

        # Fetch detail
        detail_res = test_client.get(f"/api/test/logs/{cat}/{fn}")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert "log_id" in detail_data
        assert "source_file" in detail_data
        assert "source_function" in detail_data


def test_hierarchical_logger_structure():
    """Validates logger creates files in designated category subfolders with correct schema."""
    from pathlib import Path
    logger = AvatarVoiceTestLogger()
    meta = logger.log_tts(
        text="Test logging sentence",
        language="en",
        provider="fallback",
        avatar_cue="neutral",
        duration_sec=1.5,
        word_count=3,
        vtt_path="mock.vtt",
        audio_path="mock.wav",
        source_file="modules/avatar_voice/src/tts/fallback_adapter.py",
        source_function="synthesize",
    )

    log_path = Path(meta["log_path"])
    assert log_path.exists()
    assert "tts/" in meta["relative_log"]

    # Verify JSON content
    import json
    with open(meta["json_path"], "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    assert saved_data["log_id"] == meta["log_id"]
    assert saved_data["source_file"] == "modules/avatar_voice/src/tts/fallback_adapter.py"
    assert saved_data["source_function"] == "synthesize"
    assert saved_data["status"] == "success"
