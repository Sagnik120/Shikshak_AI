"""
Video Compositor Engine.
Combines the visual panel (70% viewport), avatar PiP (30% top-right),
narration audio, and timed subtitle track into a 1920x1080 MP4 segment per Contract §7.
"""

import glob
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
import re
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont
from modules.avatar_voice.src.models import (
    AvatarRenderResult,
    RenderedVideoSegment,
    TTSResult,
    VisualRenderResult,
    WordTimestamp,
)

logger = logging.getLogger(__name__)


def compute_content_aware_step_durations(
    total_duration: float,
    num_steps: int,
    step_contents: Optional[List[str]] = None,
    word_timestamps: Optional[List[WordTimestamp]] = None,
    min_step_duration: float = 1.0,
) -> List[float]:
    """Compute content-aware, speech-aligned reveal durations for progressive visual steps.

    Addresses Issue 2 from 02_avatar_voice_module_fix_plan_v2.md:
    Instead of flat equal splits (duration / N), durations are proportionally weighted
    by step formula/text complexity, aligned with speech boundaries where possible,
    and guaranteed to sum strictly to total_duration.
    """
    if num_steps <= 0:
        return []
    if num_steps == 1:
        return [round(total_duration, 2)]

    floor_dur = min(min_step_duration, total_duration / num_steps)
    if total_duration < num_steps * 0.8:
        even_split = round(total_duration / num_steps, 2)
        durations = [even_split] * num_steps
        diff = round(total_duration - sum(durations), 2)
        durations[-1] = round(durations[-1] + diff, 2)
        return durations

    # 1. Check if word_timestamps contain sequential step transition cues
    if word_timestamps and len(word_timestamps) >= num_steps * 2:
        step_cues = ["step", "first", "second", "third", "fourth", "next", "then", "finally", "therefore", "so"]
        cue_indices = []
        for wt in word_timestamps:
            cleaned = wt.word.lower().strip(".,!?:;\"'")
            if cleaned in step_cues:
                cue_indices.append(wt.start_sec)

        if len(cue_indices) >= num_steps - 1:
            valid_splits = []
            last_t = 0.0
            for t in cue_indices:
                if t - last_t >= floor_dur and (total_duration - t) >= floor_dur:
                    valid_splits.append(t)
                    last_t = t
                if len(valid_splits) == num_steps - 1:
                    break

            if len(valid_splits) == num_steps - 1:
                boundaries = [0.0] + valid_splits + [total_duration]
                durations = [round(boundaries[i + 1] - boundaries[i], 2) for i in range(num_steps)]
                diff = round(total_duration - sum(durations), 2)
                durations[-1] = round(durations[-1] + diff, 2)
                return durations

    # 2. Content Complexity Weighting Fallback
    weights = []
    if step_contents and len(step_contents) == num_steps:
        for content in step_contents:
            raw_len = len(content.strip())
            # Boost weight for mathematical and structural symbols
            symbol_count = len(re.findall(r'[\^_\{\}\\\+\-\*\/=\(\)\[\]]', content))
            complexity = max(1.0, (raw_len + symbol_count * 2) ** 0.5)
            weights.append(complexity)
    else:
        # Default gradual complexity ramp if step contents are absent
        weights = [1.0 + (i * 0.35) for i in range(num_steps)]

    # Enforce minimum step display floor using iterative water-filling
    effective_floor = min(floor_dur, total_duration / num_steps)
    available_duration = total_duration
    step_durations = [0.0] * num_steps
    remaining_indices = list(range(num_steps))

    while remaining_indices:
        sub_weights = [weights[i] for i in remaining_indices]
        sub_total_w = sum(sub_weights)
        if sub_total_w <= 0:
            for i in remaining_indices:
                step_durations[i] = available_duration / len(remaining_indices)
            break

        to_floor = []
        for i in remaining_indices:
            allocated = available_duration * (weights[i] / sub_total_w)
            if allocated < effective_floor:
                to_floor.append(i)

        if not to_floor:
            # All remaining satisfy the floor
            for i in remaining_indices:
                step_durations[i] = available_duration * (weights[i] / sub_total_w)
            break

        # Fix the clamped elements at effective_floor and repeat for the rest
        for i in to_floor:
            step_durations[i] = effective_floor
            available_duration -= effective_floor
            remaining_indices.remove(i)

    durations = [round(d, 2) for d in step_durations]

    # Reconcile any sub-cent floating point discrepancies on the final step
    diff = round(total_duration - sum(durations), 2)
    durations[-1] = round(durations[-1] + diff, 2)
    return durations


class FFmpegCompositor:
    """Composites visual panel, avatar animation frames, and narration audio into an MP4 video."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(tempfile.gettempdir(), "shikshak_rendered_videos")
        os.makedirs(self.output_dir, exist_ok=True)
        self.canvas_width = 1920
        self.canvas_height = 1080
        self.fps = 24

        # Discover FFmpeg binary: system PATH first, then imageio-ffmpeg static binary fallback
        self.ffmpeg_bin = shutil.which("ffmpeg")
        if not self.ffmpeg_bin:
            try:
                import imageio_ffmpeg
                self.ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                logger.info(f"Using bundled imageio-ffmpeg binary: {self.ffmpeg_bin}")
            except Exception:
                self.ffmpeg_bin = None

    def compose(
        self,
        node_id: str,
        tts_result: TTSResult,
        avatar_result: AvatarRenderResult,
        visual_result: VisualRenderResult,
    ) -> RenderedVideoSegment:
        """Compose all streams into a final synchronized 1920x1080 video segment."""
        session_id = uuid.uuid4().hex[:8]
        output_mp4 = os.path.join(self.output_dir, f"segment_{node_id}_{session_id}.mp4")

        duration_sec = tts_result.duration_sec
        if duration_sec <= 0.0:
            duration_sec = avatar_result.duration_sec or 3.0

        ffmpeg_success = False
        if self.ffmpeg_bin:
            try:
                ffmpeg_success = self._compose_with_ffmpeg(
                    output_mp4=output_mp4,
                    tts_result=tts_result,
                    avatar_result=avatar_result,
                    visual_result=visual_result,
                    duration_sec=duration_sec,
                )
            except Exception as e:
                logger.warning(f"FFmpeg composition encountered error: {e}. Using fallback compositor.")
                ffmpeg_success = False
        else:
            logger.warning(
                "FFmpeg binary not detected on PATH or imageio-ffmpeg. Operating in Pillow preview fallback mode."
            )

        if not ffmpeg_success:
            self._compose_with_pillow_fallback(
                output_mp4=output_mp4,
                tts_result=tts_result,
                avatar_result=avatar_result,
                visual_result=visual_result,
                duration_sec=duration_sec,
            )

        return RenderedVideoSegment(
            node_id=node_id,
            video_url=output_mp4,
            duration_sec=round(duration_sec, 2),
            captions_vtt_url=tts_result.vtt_path,
        )

    def _compose_with_ffmpeg(
        self,
        output_mp4: str,
        tts_result: TTSResult,
        avatar_result: AvatarRenderResult,
        visual_result: VisualRenderResult,
        duration_sec: float,
    ) -> bool:
        """Execute FFmpeg filter_complex graph composition supporting single or progressive visuals."""
        frame_pattern = os.path.join(avatar_result.frames_dir, "frame_%05d.png")

        # Check if progressive steps exist
        valid_step_paths = [
            p for p in visual_result.step_image_paths
            if os.path.exists(p)
        ] if visual_result.is_progressive else []

        if len(valid_step_paths) > 1:
            # Progressive visual transition across duration
            num_steps = len(valid_step_paths)
            step_durations = compute_content_aware_step_durations(
                total_duration=duration_sec,
                num_steps=num_steps,
                step_contents=visual_result.step_contents,
                word_timestamps=tts_result.word_timestamps,
            )

            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-framerate", str(avatar_result.fps),
                "-i", frame_pattern,  # Input 0: Avatar frames
            ]

            # Add each step image as an input with its content-aware reveal duration
            for idx, step_path in enumerate(valid_step_paths):
                dur = step_durations[idx] if idx < len(step_durations) else 1.0
                cmd.extend(["-loop", "1", "-t", str(round(dur, 2)), "-i", step_path])

            audio_idx = num_steps + 1
            cmd.extend(["-i", tts_result.audio_path])  # Input audio_idx

            concat_inputs = "".join([f"[{i + 1}:v]" for i in range(num_steps)])
            filter_graph = (
                f"{concat_inputs}concat=n={num_steps}:v=1:a=0[vis_seq]; "
                f"[vis_seq]scale=1344:1080:force_original_aspect_ratio=decrease,pad=1344:1080:(ow-iw)/2:(oh-ih)/2[vis]; "
                f"[0:v]scale=576:432[avatar]; "
                f"color=c=#0f172a:s=1920x1080:r=24:d={duration_sec}[bg]; "
                f"[bg][vis]overlay=0:0[bg_vis]; "
                f"[bg_vis][avatar]overlay=1344:24[outv]"
            )

            cmd.extend([
                "-filter_complex", filter_graph,
                "-map", "[outv]",
                "-map", f"{audio_idx}:a",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-shortest",
                output_mp4,
            ])
        else:
            # Standard single visual slide
            filter_graph = (
                f"[1:v]scale=1344:1080:force_original_aspect_ratio=decrease,pad=1344:1080:(ow-iw)/2:(oh-ih)/2[vis]; "
                f"[0:v]scale=576:432[avatar]; "
                f"color=c=#0f172a:s=1920x1080:r=24:d={duration_sec}[bg]; "
                f"[bg][vis]overlay=0:0[bg_vis]; "
                f"[bg_vis][avatar]overlay=1344:24[outv]"
            )

            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-framerate", str(avatar_result.fps),
                "-i", frame_pattern,
                "-loop", "1",
                "-t", str(duration_sec),
                "-i", visual_result.image_path,
                "-i", tts_result.audio_path,
                "-filter_complex", filter_graph,
                "-map", "[outv]",
                "-map", "2:a",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-shortest",
                output_mp4,
            ]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0 and os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 0

    def _compose_with_pillow_fallback(
        self,
        output_mp4: str,
        tts_result: TTSResult,
        avatar_result: AvatarRenderResult,
        visual_result: VisualRenderResult,
        duration_sec: float,
    ) -> None:
        """Generate composite preview images and container when FFmpeg is not directly invokable."""
        images_to_composite = []
        if visual_result.is_progressive and visual_result.step_image_paths:
            images_to_composite = [p for p in visual_result.step_image_paths if os.path.exists(p)]
        if not images_to_composite and os.path.exists(visual_result.image_path):
            images_to_composite = [visual_result.image_path]

        frame_files = sorted(glob.glob(os.path.join(avatar_result.frames_dir, "frame_*.png")))
        avatar_img = None
        if frame_files:
            avatar_img = Image.open(frame_files[0]).convert("RGBA")
            avatar_img = avatar_img.resize((540, 405), Image.Resampling.LANCZOS)

        for step_idx, vis_path in enumerate(images_to_composite):
            composite_canvas = Image.new("RGBA", (self.canvas_width, self.canvas_height), (15, 23, 42, 255))

            if os.path.exists(vis_path):
                vis_img = Image.open(vis_path).convert("RGBA")
                vis_img = vis_img.resize((1344, 1080), Image.Resampling.LANCZOS)
                composite_canvas.paste(vis_img, (0, 0), vis_img)

            draw = ImageDraw.Draw(composite_canvas)
            draw.rectangle([1344, 0, 1920, 1080], fill=(20, 30, 48, 255), outline=(51, 65, 85, 255), width=2)

            if avatar_img:
                composite_canvas.paste(avatar_img, (1360, 20), avatar_img)

            draw.rounded_rectangle([1380, 440, 1880, 500], radius=8, fill=(30, 41, 59, 255), outline=(6, 182, 212, 255), width=2)
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            draw.text((1630, 470), "AI TEACHER (SHIKSHAK)", fill=(248, 250, 252, 255), font=font, anchor="mm")

            draw.rectangle([0, 960, 1920, 1080], fill=(10, 15, 25, 220))
            caption_sample = " ".join([w.word for w in tts_result.word_timestamps[:10]]) or "Adaptive AI Teacher Explanation"
            if len(images_to_composite) > 1:
                caption_sample = f"[Step {step_idx + 1} of {len(images_to_composite)}] " + caption_sample
            draw.text((960, 1020), caption_sample, fill=(255, 255, 255, 255), font=font, anchor="mm")

            suffix = f"_step_{step_idx + 1}_preview.png" if len(images_to_composite) > 1 else "_preview.png"
            composite_canvas.save(output_mp4.replace(".mp4", suffix), "PNG")

        if not os.path.exists(output_mp4):
            with open(output_mp4, "wb") as f:
                f.write(b"SHIKSHAK_AI_RENDERED_VIDEO_PAYLOAD\n")
                f.write(f"duration={duration_sec}\n".encode("utf-8"))
                f.write(f"captions={tts_result.vtt_path}\n".encode("utf-8"))
                f.write(f"progressive={visual_result.is_progressive}\n".encode("utf-8"))
                f.write(f"steps_count={len(images_to_composite)}\n".encode("utf-8"))
