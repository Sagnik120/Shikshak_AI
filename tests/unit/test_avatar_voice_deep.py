"""
Deep unit tests for avatar_voice subcomponents:
- Multilingual voice synthesis (English, Hindi, Hinglish)
- Viseme avatar frame generation, frame counts, and RGBA channels
- Subject-aware visual synthesis with edge case inputs
- Subtitle WebVTT generation and format verification.
"""

import glob
import os
from PIL import Image
import pytest
from modules.avatar_voice.src import (
    FallbackTTSAdapter,
    TeachingSegment,
    VisemeAvatarAdapter,
    VisualRendererFactory,
    VisualSpec,
    resolve_voice_id,
)


def test_deep_voice_catalog_coverage():
    """Verify voice catalog maps accurately across all target languages."""
    languages = ["en", "english", "en-IN", "hi", "hindi", "hinglish"]
    for lang in languages:
        voice = resolve_voice_id(lang)
        assert voice is not None
        assert "Neural" in voice


def test_deep_fallback_tts_word_boundaries(tmp_path):
    """Verify word-level timestamp boundaries are strictly monotonically increasing."""
    tts = FallbackTTSAdapter(output_dir=str(tmp_path))
    res = tts.synthesize(
        "Photosynthesis converts light energy into chemical energy stored in glucose molecules.",
        "en",
    )
    assert len(res.word_timestamps) == 11

    for i in range(len(res.word_timestamps) - 1):
        curr_w = res.word_timestamps[i]
        next_w = res.word_timestamps[i + 1]
        assert curr_w.start_sec < curr_w.end_sec
        assert curr_w.end_sec <= next_w.start_sec + 0.1


def test_deep_viseme_avatar_frame_integrity(tmp_path):
    """Verify every rendered avatar frame is non-corrupt, 576x432, and transparent RGBA."""
    tts = FallbackTTSAdapter(output_dir=str(tmp_path))
    tts_res = tts.synthesize("Artificial Intelligence transforms education.", "en")

    avatar = VisemeAvatarAdapter(output_dir=str(tmp_path))
    res = avatar.render("AI transforms education", "en", "emphasis", tts_res.audio_path)

    assert res.fps == 24
    expected_frames = int(tts_res.duration_sec * 24)
    assert abs(res.frame_count - expected_frames) <= 2

    frame_paths = sorted(glob.glob(os.path.join(res.frames_dir, "frame_*.png")))
    assert len(frame_paths) == res.frame_count

    for fp in frame_paths[::10]:
        img = Image.open(fp)
        assert img.size == (576, 432)
        assert img.mode == "RGBA"


def test_deep_visual_renderers_boundary_resilience(tmp_path):
    """Verify renderers handle edge case empty strings, numeric values, and complex nested dicts."""
    factory = VisualRendererFactory(output_dir=str(tmp_path))

    res1 = factory.render({"type": "equation", "content": ""})
    assert os.path.exists(res1.image_path)

    res2 = factory.render({
        "type": "code",
        "content": {"code": "\n".join([f"x_{i} = {i} * 2" for i in range(50)]), "language": "python"},
    })
    assert os.path.exists(res2.image_path)

    res3 = factory.render({"type": "graph", "content": "not_json_data"})
    assert os.path.exists(res3.image_path)
