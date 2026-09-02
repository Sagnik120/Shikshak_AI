"""
Integration tests for Video Compositing and AvatarVoiceService async job queues.
"""

import os
import time
import pytest
from modules.avatar_voice.src import (
    AvatarVoiceService,
    RenderedVideoSegment,
    TeachingSegment,
    VisualSpec,
)


def test_avatar_voice_service_sync_rendering(temp_output_dir):
    """Verify synchronous full pipeline rendering produces valid RenderedVideoSegment."""
    service = AvatarVoiceService(output_dir=temp_output_dir)
    seg = TeachingSegment(
        node_id="test_node_kinematics",
        script_text="Velocity is the rate of change of displacement with respect to time.",
        language="en",
        visual_spec=VisualSpec(type="equation", content="v = \\frac{ds}{dt}"),
        avatar_cue="emphasis",
    )

    result = service.render_segment_sync(seg)

    assert isinstance(result, RenderedVideoSegment)
    assert result.node_id == "test_node_kinematics"
    assert result.duration_sec > 0.0
    assert os.path.exists(result.video_url)
    assert result.captions_vtt_url is not None
    assert os.path.exists(result.captions_vtt_url)


def test_avatar_voice_service_async_queue(temp_output_dir):
    """Verify non-blocking job enqueueing and polling lifecycle."""
    service = AvatarVoiceService(output_dir=temp_output_dir)
    seg = TeachingSegment(
        node_id="async_node_01",
        script_text="Let us analyze the algorithm step by step.",
        language="en",
        visual_spec=VisualSpec(type="code", content="for i in range(10): print(i)"),
        avatar_cue="neutral",
    )

    job_id = service.render_segment(seg)
    assert job_id.startswith("job_")

    status = service.get_status(job_id)
    assert status is not None
    assert status.status in ["queued", "rendering", "done"]

    max_wait = 15.0
    start = time.time()
    while status and status.status != "done" and (time.time() - start) < max_wait:
        time.sleep(0.2)
        status = service.get_status(job_id)

    assert status.status == "done"
    assert status.progress_pct == 1.0
    assert status.result is not None
    assert status.result.node_id == "async_node_01"
    assert os.path.exists(status.result.video_url)
