"""
Unit tests for TTS synthesis, multilingual voices, and WebVTT caption generation.
"""

import os
import wave
import pytest
from modules.avatar_voice.src.tts import (
    EdgeTTSAdapter,
    FallbackTTSAdapter,
    ResilientTTSAdapter,
    TTSFactory,
    VOICE_CATALOG,
    resolve_voice_id,
)


def test_voice_id_resolution():
    """Verify correct neural voice short-names mapped per language."""
    assert resolve_voice_id("hi") == "hi-IN-SwaraNeural"
    assert resolve_voice_id("hindi", gender="male") == "hi-IN-MadhurNeural"
    assert resolve_voice_id("en-IN") == "en-IN-NeerjaNeural"
    assert resolve_voice_id("en-in", gender="male") == "en-IN-PrabhatNeural"
    assert resolve_voice_id("en") == "en-US-AriaNeural"
    assert resolve_voice_id("hinglish") == "hi-IN-SwaraNeural"


def test_fallback_tts_audio_and_vtt(temp_output_dir):
    """Verify offline fallback synthesizes valid 24kHz mono WAV and standard WebVTT."""
    adapter = FallbackTTSAdapter(output_dir=temp_output_dir)
    res = adapter.synthesize(
        text="Newton's second law states that force equals mass times acceleration.",
        language="en",
    )

    assert os.path.exists(res.audio_path)
    assert res.duration_sec > 0.0
    assert len(res.word_timestamps) > 5

    with wave.open(res.audio_path, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 24000
        assert wf.getsampwidth() == 2
        assert wf.getnframes() > 0

    assert os.path.exists(res.vtt_path)
    with open(res.vtt_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert content.startswith("WEBVTT")
        assert "-->" in content
        assert "Newton's" in content


def test_fallback_tts_hindi(temp_output_dir):
    """Verify offline fallback handles Hindi / Devanagari text cleanly."""
    adapter = FallbackTTSAdapter(output_dir=temp_output_dir)
    res = adapter.synthesize(
        text="न्यूटन का दूसरा नियम बताता है कि बल द्रव्यमान और त्वरण के गुणनफल के बराबर होता है।",
        language="hi",
    )
    assert res.duration_sec > 0.0
    assert len(res.word_timestamps) >= 10
    assert os.path.exists(res.vtt_path)


def test_resilient_tts_factory(temp_output_dir):
    """Verify TTSFactory returns resilient adapter and handles failover gracefully."""
    adapter = TTSFactory.get_adapter("resilient", output_dir=temp_output_dir)
    res = adapter.synthesize(text="Testing resilient synthesis.", language="en")
    assert res.duration_sec > 0.0
    assert os.path.exists(res.audio_path)
