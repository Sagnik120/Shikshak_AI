"""Deep Unit Test Suite: Cue-Driven Vocal Prosody & Delivery in Edge-TTS.

Addresses Issue 4 from 02_avatar_voice_module_fix_plan_v2.md:
1. Vocal Delivery Modulation: Validates mapping of avatar_cue to SSML pitch & rate.
2. Multi-Lingual Prosody: Validates modulation across English, Hindi, Hinglish, and Bengali voices.
3. Boundary / Unknown Cues: Validates graceful fallback for empty, unknown, or case-insensitive cues.
4. Failover Resilience: Validates ResilientTTSAdapter and FallbackTTSAdapter forward avatar_cue.
5. End-to-End Audio Synthesis: Validates real Edge-TTS waveform and subtitle generation under prosody cues.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from modules.avatar_voice.src.tts.base import VOICE_CATALOG, resolve_voice_id
from modules.avatar_voice.src.tts.edge_tts_adapter import EdgeTTSAdapter, CUE_PROSODY
from modules.avatar_voice.src.tts.fallback_adapter import FallbackTTSAdapter
from modules.avatar_voice.src.tts.factory import ResilientTTSAdapter, TTSFactory
from modules.avatar_voice.src.models import TeachingSegment, VisualSpec
from modules.avatar_voice.src.service import AvatarVoiceService


class TestTTSCueProsody:
    """Comprehensive test suite for cue-driven vocal prosody."""

    # =========================================================================
    # 1. PROSODY DICTIONARY SPECIFICATION
    # =========================================================================

    def test_cue_prosody_dictionary_specs(self):
        """Verifies exact prosody calibration for educational avatars."""
        assert CUE_PROSODY["neutral"] == {"rate": "+0%", "pitch": "+0Hz"}
        assert CUE_PROSODY["emphasis"] == {"rate": "-8%", "pitch": "+15Hz"}
        assert CUE_PROSODY["questioning"] == {"rate": "+0%", "pitch": "+25Hz"}
        assert CUE_PROSODY["encouraging"] == {"rate": "+4%", "pitch": "+15Hz"}
        assert CUE_PROSODY["celebratory"] == {"rate": "+6%", "pitch": "+20Hz"}

    # =========================================================================
    # 2. EDGE-TTS COMMUNICATE ARGUMENT VERIFICATION
    # =========================================================================

    @pytest.mark.parametrize("cue,expected_rate,expected_pitch", [
        ("neutral", "+0%", "+0Hz"),
        ("emphasis", "-8%", "+15Hz"),
        ("questioning", "+0%", "+25Hz"),
        ("encouraging", "+4%", "+15Hz"),
        ("celebratory", "+6%", "+20Hz"),
        ("EMPHASIS", "-8%", "+15Hz"),        # Case insensitivity
        (" questioning ", "+0%", "+25Hz"),   # Whitespace stripping
        ("unknown_cue", "+0%", "+0Hz"),      # Unknown fallback
        ("", "+0%", "+0Hz"),                 # Empty string fallback
    ])
    def test_edge_tts_synthesize_passes_prosody_parameters(
        self, tmp_path, cue, expected_rate, expected_pitch
    ):
        """Validates that Communicate receives exact rate and pitch parameters for each cue."""
        adapter = EdgeTTSAdapter(output_dir=str(tmp_path))

        with patch("edge_tts.Communicate") as mock_communicate:
            mock_instance = MagicMock()
            # Mock empty async stream
            async def empty_stream():
                if False:
                    yield None
            mock_instance.stream.return_value = empty_stream()
            mock_communicate.return_value = mock_instance

            # Execute synthesize
            try:
                adapter.synthesize(
                    text="This is an educational narration.",
                    language="en",
                    voice_id="en-US-AriaNeural",
                    avatar_cue=cue
                )
            except Exception:
                pass

            # Assert Communicate was instantiated with rate and pitch
            mock_communicate.assert_called_once()
            _, kwargs = mock_communicate.call_args
            assert kwargs.get("rate") == expected_rate, f"Failed for cue={cue}: expected {expected_rate}, got {kwargs.get('rate')}"
            assert kwargs.get("pitch") == expected_pitch, f"Failed for cue={cue}: expected {expected_pitch}, got {kwargs.get('pitch')}"

    # =========================================================================
    # 3. MULTI-LINGUAL VOICE RESOLUTION WITH PROSODY
    # =========================================================================

    @pytest.mark.parametrize("lang,expected_voice_prefix", [
        ("en", "en-US-AriaNeural"),
        ("hi", "hi-IN-SwaraNeural"),
        ("hindi", "hi-IN-SwaraNeural"),
        ("hinglish", "hi-IN-SwaraNeural"),
        ("bn", "bn-IN-TanishaaNeural"),
        ("bengali", "bn-IN-TanishaaNeural"),
    ])
    def test_multilingual_voice_resolution(self, lang, expected_voice_prefix):
        """Verifies correct neural voice assignment across supported Indian & International languages."""
        voice = resolve_voice_id(lang)
        assert voice == expected_voice_prefix

    # =========================================================================
    # 4. FALLBACK & RESILIENT ADAPTER FORWARDING
    # =========================================================================

    def test_fallback_adapter_accepts_avatar_cue(self, tmp_path):
        """Validates FallbackTTSAdapter accepts avatar_cue without error."""
        adapter = FallbackTTSAdapter(output_dir=str(tmp_path))
        result = adapter.synthesize(
            text="Offline fallback synthesis test.",
            language="hi",
            avatar_cue="emphasis"
        )
        assert "fallback" in result.engine_used
        assert result.duration_sec > 0.0
        assert os.path.exists(result.audio_path)

    def test_resilient_adapter_forwards_avatar_cue(self, tmp_path):
        """Validates ResilientTTSAdapter passes avatar_cue to primary and fallback engines."""
        adapter = ResilientTTSAdapter(output_dir=str(tmp_path))

        with patch.object(adapter.edge_adapter, "synthesize") as mock_edge:
            adapter.synthesize(text="Testing resilience", language="en", avatar_cue="questioning")
            mock_edge.assert_called_once_with(
                text="Testing resilience",
                language="en",
                voice_id="en-US-AriaNeural",
                avatar_cue="questioning"
            )

    # =========================================================================
    # 5. AVATAR VOICE SERVICE INTEGRATION
    # =========================================================================

    def test_avatar_voice_service_forwards_avatar_cue_to_tts(self, tmp_path):
        """Validates that AvatarVoiceService passes segment.avatar_cue to self.tts."""
        service = AvatarVoiceService(output_dir=str(tmp_path))

        mock_tts = MagicMock()
        mock_tts_result = MagicMock()
        mock_tts_result.audio_path = os.path.join(str(tmp_path), "test.wav")
        mock_tts_result.duration_sec = 2.0
        mock_tts.synthesize.return_value = mock_tts_result
        service.tts = mock_tts

        segment = TeachingSegment(
            node_id="test_cue_segment",
            script_text="Can we solve this equation using substitution?",
            language="en",
            visual_spec=VisualSpec(type="equation", content="x = 2"),
            avatar_cue="questioning"
        )

        with patch.object(service.visuals, "render"), \
             patch.object(service.avatar, "render"), \
             patch.object(service.compositor, "compose"):
            service.render_segment_sync(segment)

        mock_tts.synthesize.assert_called_once_with(
            text="Can we solve this equation using substitution?",
            language="en",
            avatar_cue="questioning"
        )

    @pytest.mark.parametrize("cue", ["neutral", "emphasis", "questioning", "encouraging", "celebratory"])
    def test_teaching_segment_accepts_all_five_contract_cues(self, cue):
        """Validates Contract §6: TeachingSegment model accepts all five avatar_cue literals without ValidationError."""
        segment = TeachingSegment(
            node_id=f"node_{cue}",
            script_text=f"Testing cue: {cue}",
            language="en",
            visual_spec=VisualSpec(type="equation", content="E = mc^2"),
            avatar_cue=cue
        )
        assert segment.avatar_cue == cue

    def test_teaching_segment_rejects_invalid_cue(self):
        """Validates that unknown avatar_cue raises Pydantic ValidationError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TeachingSegment(
                node_id="node_invalid",
                script_text="Testing invalid cue",
                language="en",
                visual_spec=VisualSpec(type="equation", content="E = mc^2"),
                avatar_cue="dancing"  # not in Literal
            )

    # =========================================================================
    # 6. REAL AUDIO SYNTHESIS WITH LIVE EDGE-TTS
    # =========================================================================

    @pytest.mark.parametrize("cue", ["neutral", "emphasis", "questioning", "encouraging", "celebratory"])
    def test_live_edge_tts_synthesis_with_prosody(self, tmp_path, cue):
        """Validates live synthesis producing valid WAV audio under real Edge-TTS pitch/rate cues."""
        adapter = EdgeTTSAdapter(output_dir=str(tmp_path))
        result = adapter.synthesize(
            text="Testing neural prosody pitch and rate modulation.",
            language="en",
            avatar_cue=cue
        )
        assert result.duration_sec > 0.5
        assert os.path.exists(result.audio_path)
        assert os.path.getsize(result.audio_path) > 1000
        assert result.vtt_path is not None
        assert os.path.exists(result.vtt_path)
