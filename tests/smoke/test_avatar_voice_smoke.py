"""
Smoke tests for avatar_voice module.
Validates rapid initialization, basic synthesis, and contract compatibility.
"""

import os
import pytest
from modules.avatar_voice.src import (
    AvatarVoiceService,
    RenderedVideoSegment,
    TeachingSegment,
    VisualSpec,
)


def test_avatar_voice_smoke_init():
    """Verify avatar_voice service initializes cleanly without exceptions."""
    service = AvatarVoiceService()
    assert service is not None
    assert service.tts is not None
    assert service.avatar is not None
    assert service.visuals is not None
    assert service.compositor is not None


def test_avatar_voice_smoke_render(tmp_path):
    """Smoke test: execute a fast render of a teaching segment."""
    service = AvatarVoiceService(output_dir=str(tmp_path))
    seg = TeachingSegment(
        node_id="smoke_node_01",
        script_text="Welcome to Shikshak AI.",
        language="en",
        visual_spec=VisualSpec(type="equation", content="E=mc^2"),
        avatar_cue="neutral",
    )
    result = service.render_segment_sync(seg)
    assert isinstance(result, RenderedVideoSegment)
    assert result.node_id == "smoke_node_01"
    assert result.duration_sec > 0.0
    assert os.path.exists(result.video_url)
