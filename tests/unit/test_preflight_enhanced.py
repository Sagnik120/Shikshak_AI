"""Deep Unit Test Suite: Cross-Platform Preflight Diagnostic Enhancements.

Addresses Issue 3 from 02_avatar_voice_module_fix_plan_v2.md:
1. --require-ffmpeg: Validates strict exit code 1 when FFmpeg is absent, code 0 when present.
2. --check-tier2: Validates strict exit code 1 when Tier 2 prerequisites are absent.
3. --json: Validates machine-readable JSON schema output for CI/CD pipelines.
4. Subsystem Coverage: Validates Bengali, Devanagari, and SSML vocal prosody checks.
"""

import json
import pytest
from unittest.mock import patch
from scripts.preflight_check import (
    main,
    check_ffmpeg,
    check_tier2_musetalk,
    check_vocal_prosody,
    check_multilingual_parser,
    check_rag_chroma,
    check_dependencies,
)


class TestPreflightEnhanced:
    """Comprehensive test suite for preflight diagnostic CLI flags and subsystem health."""

    def test_preflight_standard_execution_returns_zero(self):
        """Validates that standard preflight execution on configured host passes."""
        exit_code = main([])
        assert exit_code == 0

    def test_preflight_json_flag_emits_valid_schema(self, capsys):
        """Validates that --json outputs structured dictionary with required keys."""
        exit_code = main(["--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)

        assert "platform" in data
        assert "python_version" in data
        assert "dependencies" in data
        assert "subsystems" in data
        assert "overall_status" in data
        assert "exit_code" in data
        assert data["exit_code"] == exit_code

        # Verify key subsystems are present in output
        subsystem_names = [s["name"] for s in data["subsystems"]]
        assert "FFmpeg Binary" in subsystem_names
        assert "Multilingual (Indic)" in subsystem_names
        assert "Vocal Delivery Prosody" in subsystem_names
        assert "Tier 2 MuseTalk Neural" in subsystem_names

    def test_preflight_require_ffmpeg_fails_when_ffmpeg_missing(self):
        """Validates --require-ffmpeg returns exit code 1 if FFmpeg is not found."""
        with patch("scripts.preflight_check.check_ffmpeg", return_value=("FFmpeg Binary", "WARN", "Not found")):
            exit_code = main(["--require-ffmpeg"])
            assert exit_code == 1

    def test_preflight_require_ffmpeg_passes_when_ffmpeg_present(self):
        """Validates --require-ffmpeg returns exit code 0 when FFmpeg is present."""
        with patch("scripts.preflight_check.check_ffmpeg", return_value=("FFmpeg Binary", "PASS", "Found")):
            exit_code = main(["--require-ffmpeg"])
            assert exit_code == 0

    def test_preflight_check_tier2_fails_when_cuda_or_weights_missing(self):
        """Validates --check-tier2 returns exit code 1 when Tier 2 neural model cannot run."""
        with patch(
            "scripts.preflight_check.check_tier2_musetalk",
            return_value=("Tier 2 MuseTalk Neural", "INFO", "Tier 1 active; CUDA GPU unavailable")
        ):
            exit_code = main(["--check-tier2"])
            assert exit_code == 1

    def test_preflight_check_tier2_passes_when_tier2_ready(self):
        """Validates --check-tier2 returns exit code 0 when Tier 2 neural model is ready."""
        with patch(
            "scripts.preflight_check.check_tier2_musetalk",
            return_value=("Tier 2 MuseTalk Neural", "PASS", "CUDA GPU and weights verified")
        ):
            exit_code = main(["--check-tier2"])
            assert exit_code == 0

    def test_subsystem_multilingual_parser_diagnostics(self):
        """Verifies Bengali and Hindi script parser diagnostic returns PASS."""
        name, status, detail = check_multilingual_parser()
        assert status == "PASS"
        assert "bengali" in detail.lower()
        assert "devanagari" in detail.lower()

    def test_subsystem_vocal_prosody_diagnostics(self):
        """Verifies vocal prosody check returns PASS."""
        name, status, detail = check_vocal_prosody()
        assert status == "PASS"
        assert "ssml" in detail.lower() or "prosody" in detail.lower()

    def test_subsystem_chroma_diagnostics_operational(self):
        """Verifies ChromaDB diagnostic returns PASS on functional environment."""
        name, status, detail = check_rag_chroma()
        assert name == "ChromaDB Storage"
        assert status == "PASS"
        assert "operational" in detail.lower()

    def test_subsystem_chroma_diagnostics_fails_loud_on_missing_import(self):
        """Verifies ChromaDB diagnostic returns FAIL when chromadb cannot be imported."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "chromadb":
                raise ImportError("No module named 'chromadb'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            name, status, detail = check_rag_chroma()
            assert name == "ChromaDB Storage"
            assert status == "FAIL"
            assert "pip install chromadb" in detail

    def test_subsystem_chroma_diagnostics_fails_loud_on_mock_client(self):
        """Verifies ChromaDB diagnostic returns FAIL when ChromaVectorStoreAdapter client drops to mock."""
        from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
        with patch.object(ChromaVectorStoreAdapter, "_get_client", return_value="mock"):
            name, status, detail = check_rag_chroma()
            assert name == "ChromaDB Storage"
            assert status == "FAIL"
            assert "mock" in detail.lower()

    def test_check_dependencies_includes_edge_tts_and_matplotlib(self):
        """Verifies check_dependencies checks edge_tts, imageio_ffmpeg, and matplotlib."""
        results = check_dependencies()
        pkg_names = [pkg for pkg, status, desc in results]
        assert "edge_tts" in pkg_names
        assert "imageio_ffmpeg" in pkg_names
        assert "matplotlib" in pkg_names
        assert "chromadb" in pkg_names
