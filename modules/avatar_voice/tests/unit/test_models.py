"""
Unit tests for avatar_voice domain models and Contract schemas.
"""

import pytest
from pydantic import ValidationError
from modules.avatar_voice.src.models import (
    AvatarRenderResult,
    RenderJobStatus,
    RenderedVideoSegment,
    TeachingSegment,
    TTSResult,
    VisualRenderResult,
    VisualSpec,
    WordTimestamp,
)


def test_teaching_segment_valid():
    """Verify standard TeachingSegment matching Contract §6."""
    seg = TeachingSegment(
        node_id="node_calculus_01",
        script_text="Today we explore derivatives and rates of change.",
        language="en",
        visual_spec=VisualSpec(type="equation", content="f'(x) = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}"),
        avatar_cue="emphasis",
    )
    assert seg.node_id == "node_calculus_01"
    assert seg.avatar_cue == "emphasis"
    assert seg.visual_spec.type == "equation"


def test_rendered_video_segment_valid():
    """Verify standard RenderedVideoSegment matching Contract §7."""
    res = RenderedVideoSegment(
        node_id="node_calculus_01",
        video_url="/storage/videos/node_calculus_01.mp4",
        duration_sec=14.5,
        captions_vtt_url="/storage/captions/node_calculus_01.vtt",
    )
    assert res.node_id == "node_calculus_01"
    assert res.duration_sec == 14.5
    assert res.captions_vtt_url.endswith(".vtt")


def test_teaching_segment_invalid_cue():
    """Reject non-contract avatar cue values."""
    with pytest.raises(ValidationError):
        TeachingSegment(
            node_id="node_1",
            script_text="Hello",
            language="en",
            visual_spec=VisualSpec(type="equation", content="x=1"),
            avatar_cue="laughing_loudly",
        )


def test_word_timestamp_and_tts_result():
    """Verify internal TTSResult and WordTimestamp schemas."""
    w1 = WordTimestamp(word="Physics", start_sec=0.0, end_sec=0.45)
    w2 = WordTimestamp(word="Gravity", start_sec=0.50, end_sec=0.95)
    tts = TTSResult(
        audio_path="/tmp/test.wav",
        duration_sec=1.2,
        word_timestamps=[w1, w2],
        vtt_path="/tmp/test.vtt",
        engine_used="edge-tts",
    )
    assert len(tts.word_timestamps) == 2
    assert tts.word_timestamps[0].word == "Physics"


def test_render_job_status():
    """Verify asynchronous job status progression model."""
    status = RenderJobStatus(
        job_id="job_12345",
        status="rendering",
        progress_pct=0.45,
        stage="animating_avatar",
    )
    assert status.status == "rendering"
    assert status.progress_pct == 0.45
