"""
AvatarVoiceService Facade & Async Rendering Queue.
Provides non-blocking job queuing and synchronous rendering methods matching Contract §6 and §7.
"""

import concurrent.futures
import logging
import threading
import uuid
from typing import Dict, Optional, Union
from modules.avatar_voice.src.avatar.base import AvatarAdapter
from modules.avatar_voice.src.avatar.viseme_avatar import VisemeAvatarAdapter
from modules.avatar_voice.src.compositor.ffmpeg_compositor import FFmpegCompositor
from modules.avatar_voice.src.models import (
    RenderJobStatus,
    RenderedVideoSegment,
    TeachingSegment,
    VisualSpec,
)
from modules.avatar_voice.src.tts.base import TTSAdapter
from modules.avatar_voice.src.tts.factory import TTSFactory
from modules.avatar_voice.src.visuals.factory import VisualRendererFactory

logger = logging.getLogger(__name__)


class AvatarVoiceService:
    """Unified service facade for Multilingual Voice Synthesis, Avatar Animation & Video Compositing."""

    def __init__(
        self,
        tts_adapter: Optional[TTSAdapter] = None,
        avatar_adapter: Optional[AvatarAdapter] = None,
        output_dir: Optional[str] = None,
        max_workers: int = 4,
    ):
        self.tts = tts_adapter or TTSFactory.get_adapter("resilient", output_dir=output_dir)
        self.avatar = avatar_adapter or VisemeAvatarAdapter(output_dir=output_dir)
        self.visuals = VisualRendererFactory(output_dir=output_dir)
        self.compositor = FFmpegCompositor(output_dir=output_dir)

        self._jobs: Dict[str, RenderJobStatus] = {}
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def render_segment_sync(self, segment: Union[TeachingSegment, Dict]) -> RenderedVideoSegment:
        """Synchronously execute the full pipeline."""
        if isinstance(segment, dict):
            segment = TeachingSegment(**segment)

        node_id = segment.node_id
        script_text = segment.script_text
        language = segment.language
        visual_spec = segment.visual_spec
        avatar_cue = segment.avatar_cue

        # 1. TTS Synthesis
        tts_result = self.tts.synthesize(text=script_text, language=language)

        # 2. Visual Synthesis
        visual_result = self.visuals.render(visual_spec)

        # 3. Avatar Animation
        avatar_result = self.avatar.render(
            script_text=script_text,
            language=language,
            avatar_cue=avatar_cue,
            audio_path=tts_result.audio_path,
        )

        # 4. Video Compositing
        rendered_segment = self.compositor.compose(
            node_id=node_id,
            tts_result=tts_result,
            avatar_result=avatar_result,
            visual_result=visual_result,
        )

        return rendered_segment

    def render_segment(self, segment: Union[TeachingSegment, Dict]) -> str:
        """Asynchronously enqueue a video rendering job."""
        if isinstance(segment, dict):
            seg_obj = TeachingSegment(**segment)
        else:
            seg_obj = segment

        job_id = f"job_{uuid.uuid4().hex[:10]}"
        with self._lock:
            self._jobs[job_id] = RenderJobStatus(
                job_id=job_id,
                status="queued",
                progress_pct=0.0,
                stage="enqueued",
            )

        self._executor.submit(self._execute_async_job, job_id, seg_obj)
        return job_id

    def _execute_async_job(self, job_id: str, segment: TeachingSegment) -> None:
        """Worker task processing the video rendering pipeline."""
        try:
            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id].status = "rendering"
                    self._jobs[job_id].progress_pct = 0.25
                    self._jobs[job_id].stage = "synthesizing_audio_and_visuals"

            tts_result = self.tts.synthesize(text=segment.script_text, language=segment.language)
            visual_result = self.visuals.render(segment.visual_spec)

            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id].progress_pct = 0.60
                    self._jobs[job_id].stage = "animating_avatar"

            avatar_result = self.avatar.render(
                script_text=segment.script_text,
                language=segment.language,
                avatar_cue=segment.avatar_cue,
                audio_path=tts_result.audio_path,
            )

            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id].progress_pct = 0.85
                    self._jobs[job_id].stage = "compositing_video"

            rendered = self.compositor.compose(
                node_id=segment.node_id,
                tts_result=tts_result,
                avatar_result=avatar_result,
                visual_result=visual_result,
            )

            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id].status = "done"
                    self._jobs[job_id].progress_pct = 1.0
                    self._jobs[job_id].stage = "completed"
                    self._jobs[job_id].result = rendered

        except Exception as e:
            logger.exception(f"Async render job {job_id} failed: {e}")
            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id].status = "failed"
                    self._jobs[job_id].error = str(e)
                    self._jobs[job_id].stage = "error"

    def get_status(self, job_id: str) -> Optional[RenderJobStatus]:
        """Poll the current progress and result of a background rendering job."""
        with self._lock:
            return self._jobs.get(job_id)
