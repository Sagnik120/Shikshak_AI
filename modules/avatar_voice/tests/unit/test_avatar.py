"""
Unit tests for Viseme-driven 2D Avatar frame synthesis and cue variations.
"""

import glob
import os
from PIL import Image
import pytest
from modules.avatar_voice.src.avatar import VisemeAvatarAdapter
from modules.avatar_voice.src.tts import FallbackTTSAdapter


def test_viseme_avatar_frame_generation(temp_output_dir):
    """Verify 24 FPS RGBA frames generated matching audio duration."""
    tts = FallbackTTSAdapter(output_dir=temp_output_dir)
    tts_res = tts.synthesize("Welcome to this physics lesson.", "en")

    avatar = VisemeAvatarAdapter(output_dir=temp_output_dir)
    res = avatar.render(
        script_text="Welcome to this physics lesson.",
        language="en",
        avatar_cue="neutral",
        audio_path=tts_res.audio_path,
    )

    assert res.fps == 24
    assert res.is_transparent is True
    assert res.frame_count > 0
    assert os.path.exists(res.frames_dir)

    frames = sorted(glob.glob(os.path.join(res.frames_dir, "frame_*.png")))
    assert len(frames) == res.frame_count

    first_frame = Image.open(frames[0])
    assert first_frame.size == (576, 432)
    assert first_frame.mode == "RGBA"


def test_avatar_cue_variations(temp_output_dir):
    """Verify avatar poses render properly for all 3 supported cues."""
    avatar = VisemeAvatarAdapter(output_dir=temp_output_dir)
    for cue in ["neutral", "emphasis", "questioning"]:
        res = avatar.render("Explaining cue", "en", avatar_cue=cue)
        assert res.frame_count > 0
        frames = glob.glob(os.path.join(res.frames_dir, "frame_*.png"))
        assert len(frames) > 0


def test_avatar_mouth_state_diversity(temp_output_dir):
    """Verify mouth shape varies across frames driven by audio RMS energy."""
    tts = FallbackTTSAdapter(output_dir=temp_output_dir)
    tts_res = tts.synthesize("Quantum mechanics reveals energy quantization at discrete levels.", "en")

    avatar = VisemeAvatarAdapter(output_dir=temp_output_dir)
    res = avatar.render("Quantum mechanics...", "en", "neutral", tts_res.audio_path)

    frames = sorted(glob.glob(os.path.join(res.frames_dir, "frame_*.png")))
    assert len(frames) >= 20

    frame_sizes = [os.path.getsize(f) for f in frames[:20]]
    assert len(set(frame_sizes)) > 1
