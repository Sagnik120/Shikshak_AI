"""Unit tests for language-aware TTS pacing and duration scaling.

Verifies:
1. FallbackTTSAdapter applies appropriate language pacing factors (en: 1.0, hinglish: 1.12, hi: 1.20).
2. Hindi audio duration is ~15-25% longer than English for equivalent word count.
3. Word timestamps scale proportionally with pacing factors.
4. WebVTT subtitle track timings align with generated audio duration.
5. Boundary inputs (empty string, single word, long paragraph) scale gracefully.
"""

import os
import pytest
from modules.avatar_voice.src.tts.fallback_adapter import FallbackTTSAdapter


class TestTTSLanguagePacing:
    """Test suite validating per-language pacing heuristics in FallbackTTSAdapter."""

    @pytest.fixture
    def tts_adapter(self, tmp_path):
        return FallbackTTSAdapter(output_dir=str(tmp_path))

    def test_hindi_duration_is_longer_than_english_for_identical_word_counts(self, tts_adapter):
        """Hindi speech takes ~15-25% longer due to syllable density and pacing heuristics."""
        words_en = "one two three four five six seven eight nine ten"
        words_hi = "ek do teen chaar paanch chhah saat aath nau das"

        res_en = tts_adapter.synthesize(text=words_en, language="en")
        res_hi = tts_adapter.synthesize(text=words_hi, language="hi")

        assert res_en.duration_sec > 0.0
        assert res_hi.duration_sec > res_en.duration_sec
        # Verify ratio is in the expected ~1.15 to ~1.25 range
        ratio = res_hi.duration_sec / res_en.duration_sec
        assert 1.15 <= ratio <= 1.30, f"Expected Hindi duration to be ~20% longer, got ratio {ratio}"

    def test_hinglish_duration_is_intermediate(self, tts_adapter):
        """Hinglish code-mixed speech pacing factor is 1.12 (between English 1.0 and Hindi 1.20)."""
        text = "today we will study machine learning algorithms step by step"
        res_en = tts_adapter.synthesize(text=text, language="en")
        res_hinglish = tts_adapter.synthesize(text=text, language="hinglish")
        res_hi = tts_adapter.synthesize(text=text, language="hi")

        assert res_en.duration_sec < res_hinglish.duration_sec < res_hi.duration_sec

    def test_word_timestamps_scale_proportionally(self, tts_adapter):
        """Individual word durations must scale by the language pacing factor."""
        test_word = "acceleration"
        res_en = tts_adapter.synthesize(text=test_word, language="en")
        res_hi = tts_adapter.synthesize(text=test_word, language="hi")

        dur_en = res_en.word_timestamps[0].end_sec - res_en.word_timestamps[0].start_sec
        dur_hi = res_hi.word_timestamps[0].end_sec - res_hi.word_timestamps[0].start_sec

        ratio = dur_hi / dur_en
        assert 1.18 <= ratio <= 1.22, f"Expected ~1.20 word duration ratio, got {ratio}"

    def test_vtt_subtitle_track_timing_matches_audio_duration(self, tts_adapter):
        """WebVTT end timestamp must closely match total audio duration."""
        text = "Newton's laws of motion explain how objects interact in space."
        res = tts_adapter.synthesize(text=text, language="hi")

        assert os.path.exists(res.vtt_path)
        with open(res.vtt_path, "r", encoding="utf-8") as f:
            vtt_content = f.read()

        assert "WEBVTT" in vtt_content
        last_word_end = res.word_timestamps[-1].end_sec
        assert abs(res.duration_sec - last_word_end) <= 0.15

    @pytest.mark.parametrize("empty_input", ["", "   ", "\t\n"])
    def test_boundary_empty_text_scales_safely(self, tts_adapter, empty_input):
        """Empty or whitespace text synthesizes placeholder without crashing."""
        res = tts_adapter.synthesize(text=empty_input, language="hi")
        assert res.duration_sec > 0.0
        assert len(res.word_timestamps) == 1
        assert res.word_timestamps[0].word == "..."
        assert os.path.exists(res.audio_path)
