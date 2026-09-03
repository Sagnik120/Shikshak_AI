"""Deep Unit Test Suite: MuseTalk Neural Avatar Architecture & Transparent Tier Reporting.

Addresses Issue 1 from 02_avatar_voice_module_fix_plan_v2.md:
1. Transparent Tier Reporting: Validates tier_used and tier_used_reason in AvatarRenderResult.
2. Graceful Fallback: Validates seamless fallback to Tier 1 visemes under CPU/headless hosts.
3. Diagnostic Environment Inspection: Validates CUDA device check and checkpoint path verification.
4. Factory Engine Resolution: Validates AvatarFactory resolution across auto, tier1, and tier2.
5. Service Pipeline Integration: Validates that AvatarVoiceService executes with transparent tier reporting.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from modules.avatar_voice.src.avatar.viseme_avatar import VisemeAvatarAdapter
from modules.avatar_voice.src.avatar.musetalk_avatar import MuseTalkAvatarAdapter
from modules.avatar_voice.src.avatar.factory import AvatarFactory
from modules.avatar_voice.src.models import TeachingSegment, VisualSpec
from modules.avatar_voice.src.service import AvatarVoiceService


class TestMuseTalkTierReporting:
    """Comprehensive test suite for Tier 1 and Tier 2 avatar architecture & transparent reporting."""

    # =========================================================================
    # 1. TIER 1 VISEME ADAPTER REPORTING
    # =========================================================================

    def test_tier1_viseme_adapter_reports_explicit_metadata(self, tmp_path):
        """Validates that VisemeAvatarAdapter populates tier_used and tier_used_reason."""
        adapter = VisemeAvatarAdapter(output_dir=str(tmp_path))
        res = adapter.render(
            script_text="Hello students, welcome to physics.",
            language="en",
            avatar_cue="neutral",
            audio_path=""
        )

        assert res.tier == "tier1_viseme"
        assert res.tier_used == "tier1_viseme"
        assert res.tier_used_reason is not None
        assert "tier 1" in res.tier_used_reason.lower()
        assert res.frame_count > 0
        assert os.path.exists(res.frames_dir)

    # =========================================================================
    # 2. TIER 2 MUSETALK DIAGNOSTICS & GRACEFUL FALLBACK
    # =========================================================================

    def test_musetalk_adapter_diagnoses_missing_prerequisites_and_falls_back(self, tmp_path):
        """Under CPU/headless environment without checkpoints, MuseTalk transparently falls back to Tier 1."""
        adapter = MuseTalkAvatarAdapter(
            checkpoint_dir=str(tmp_path / "non_existent_weights"),
            output_dir=str(tmp_path),
            force_tier2=False,
            test_mode=False
        )

        diag = adapter.diagnose_environment()
        assert diag["ready"] is False
        assert "unavailable" in diag["reason"].lower() or "not found" in diag["reason"].lower()

        res = adapter.render(
            script_text="This lesson explains neural lip sync fallback.",
            language="en",
            avatar_cue="emphasis",
            audio_path=""
        )

        # Transparently reports tier1_viseme with exact diagnostic reason
        assert res.tier_used == "tier1_viseme"
        assert res.tier_used_reason is not None
        assert "graceful fallback" in res.tier_used_reason.lower()
        assert res.frame_count > 0

    # =========================================================================
    # 3. TIER 2 FORCED EXECUTION ERROR REPORTING
    # =========================================================================

    def test_musetalk_adapter_raises_actionable_error_when_forced_without_prerequisites(self, tmp_path):
        """When force_tier2=True and prerequisites are absent, raises RuntimeError with download instructions."""
        adapter = MuseTalkAvatarAdapter(
            checkpoint_dir="/tmp/missing_musetalk_weights",
            output_dir=str(tmp_path),
            force_tier2=True,
            test_mode=False
        )

        with pytest.raises(RuntimeError) as exc_info:
            adapter.render(
                script_text="Forced Tier 2 test.",
                language="en",
                avatar_cue="neutral",
                audio_path=""
            )

        err_msg = str(exc_info.value)
        assert "MuseTalk Tier 2 execution forced" in err_msg
        assert "download MuseTalk checkpoints" in err_msg
        assert "/tmp/missing_musetalk_weights" in err_msg

    # =========================================================================
    # 4. TIER 2 ACTIVE NEURAL EXECUTION (TEST / ACCELERATED MODE)
    # =========================================================================

    def test_musetalk_adapter_renders_tier2_when_ready(self, tmp_path):
        """When running in test_mode or on GPU host with weights, MuseTalk outputs tier2_musetalk."""
        adapter = MuseTalkAvatarAdapter(
            checkpoint_dir=str(tmp_path),
            output_dir=str(tmp_path),
            force_tier2=False,
            test_mode=True  # Simulates active neural inference
        )

        diag = adapter.diagnose_environment()
        assert diag["ready"] is True

        res = adapter.render(
            script_text="Active MuseTalk neural synthesis.",
            language="en",
            avatar_cue="questioning",
            audio_path=""
        )

        assert res.tier == "tier2_musetalk"
        assert res.tier_used == "tier2_musetalk"
        assert "neural lip-sync active" in res.tier_used_reason.lower()
        assert res.frame_count > 0

    # =========================================================================
    # 5. AVATAR FACTORY RESOLUTION
    # =========================================================================

    def test_avatar_factory_engine_resolution(self, tmp_path):
        """Validates that AvatarFactory instantiates appropriate adapters according to tier flag."""
        # Tier 1 procedural
        t1_adapter = AvatarFactory.get_adapter("tier1", output_dir=str(tmp_path))
        assert isinstance(t1_adapter, VisemeAvatarAdapter)

        # Tier 2 neural
        t2_adapter = AvatarFactory.get_adapter("tier2", output_dir=str(tmp_path), test_mode=True)
        assert isinstance(t2_adapter, MuseTalkAvatarAdapter)
        assert t2_adapter.force_tier2 is True

        # Auto detection
        auto_adapter = AvatarFactory.get_adapter("auto", output_dir=str(tmp_path))
        assert isinstance(auto_adapter, MuseTalkAvatarAdapter)
        assert auto_adapter.force_tier2 is False

    # =========================================================================
    # 6. SERVICE PIPELINE INTEGRATION WITH TRANSPARENT REPORTING
    # =========================================================================

    def test_avatar_voice_service_transparent_tier_reporting(self, tmp_path):
        """Validates full end-to-end service execution with transparent avatar tier reporting."""
        service = AvatarVoiceService(output_dir=str(tmp_path))

        segment = TeachingSegment(
            node_id="test_tier_transparency",
            script_text="Let us verify avatar tier reporting.",
            language="en",
            visual_spec=VisualSpec(type="equation", content="y = mx + c"),
            avatar_cue="neutral"
        )

        # Run pipeline
        rendered = service.render_segment_sync(segment)
        assert rendered.node_id == "test_tier_transparency"
        assert rendered.duration_sec > 0.0
        assert os.path.exists(rendered.video_url)

        # Inspect that avatar adapter inside service populated tier_used
        adapter_res = service.avatar.render(
            script_text=segment.script_text,
            language=segment.language,
            avatar_cue=segment.avatar_cue
        )
        assert adapter_res.tier_used in ("tier1_viseme", "tier2_musetalk")
        assert adapter_res.tier_used_reason is not None

    # =========================================================================
    # 7. BOUNDARY: REAL DIRECTORY WITH WEIGHTS PRESENT
    # =========================================================================

    def test_musetalk_detects_synthesized_checkpoint_weights(self, tmp_path):
        """Validates that checkpoint directory containing weight files is recognized."""
        weights_dir = tmp_path / "mock_musetalk_weights"
        weights_dir.mkdir(parents=True)
        (weights_dir / "musetalk.json").write_text("{}")
        (weights_dir / "pytorch_model.bin").write_bytes(b"\x00" * 64)

        adapter = MuseTalkAvatarAdapter(checkpoint_dir=str(weights_dir), output_dir=str(tmp_path))
        diag = adapter.diagnose_environment()
        assert diag["weights_present"] is True
        assert diag["checkpoint_dir"] == str(weights_dir)
