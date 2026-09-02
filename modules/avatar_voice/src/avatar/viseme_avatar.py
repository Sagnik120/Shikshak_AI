"""
Viseme-driven 2D Avatar Adapter (Tier 1 MVP).
Generates an expressive teacher avatar whose mouth movements synchronise with
the audio RMS energy envelope at 24 FPS with transparent RGBA frame output.
"""

import math
import os
import struct
import tempfile
import uuid
import wave
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import AvatarRenderResult


class VisemeAvatarAdapter:
    """Tier-1 MVP viseme-based animated teacher avatar."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(tempfile.gettempdir(), "shikshak_avatar")
        os.makedirs(self.output_dir, exist_ok=True)
        self.width = 576
        self.height = 432
        self.fps = 24

    def render(
        self, script_text: str, language: str, avatar_cue: str = "neutral", audio_path: str = ""
    ) -> AvatarRenderResult:
        """Render 24 FPS transparent RGBA frame sequence driven by audio RMS envelope."""
        session_id = uuid.uuid4().hex[:8]
        frames_dir = os.path.join(self.output_dir, f"avatar_{session_id}")
        os.makedirs(frames_dir, exist_ok=True)

        rms_envelope, duration_sec = self._extract_rms_envelope(audio_path, self.fps)
        num_frames = max(1, len(rms_envelope))

        closed_img = self._generate_avatar_sprite(avatar_cue, mouth_state="closed")
        half_img = self._generate_avatar_sprite(avatar_cue, mouth_state="half_open")
        open_img = self._generate_avatar_sprite(avatar_cue, mouth_state="open")

        for frame_idx, energy in enumerate(rms_envelope):
            if energy < 0.15:
                frame_img = closed_img
            elif energy < 0.50:
                frame_img = half_img
            else:
                frame_img = open_img

            frame_filename = os.path.join(frames_dir, f"frame_{frame_idx:05d}.png")
            frame_img.save(frame_filename, "PNG")

        return AvatarRenderResult(
            frames_dir=frames_dir,
            frame_count=num_frames,
            fps=self.fps,
            duration_sec=duration_sec,
            is_transparent=True,
            tier="tier1_viseme",
        )

    def _extract_rms_envelope(self, audio_path: str, fps: int) -> Tuple[List[float], float]:
        """Extract frame-by-frame RMS energy from WAV audio file."""
        if not audio_path or not os.path.exists(audio_path):
            duration = 3.0
            num_frames = int(duration * fps)
            envelope = [0.2 + 0.4 * abs(math.sin(i * 0.4)) for i in range(num_frames)]
            return envelope, duration

        try:
            with wave.open(audio_path, "rb") as wf:
                sample_rate = wf.getframerate()
                num_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                num_samples = wf.getnframes()
                duration = num_samples / float(sample_rate)
                raw_bytes = wf.readframes(num_samples)

            samples_per_frame = int(sample_rate / fps)
            total_frames = max(1, int(duration * fps))

            if sampwidth == 2:
                fmt = f"<{num_samples * num_channels}h"
                data = struct.unpack(fmt, raw_bytes)
                if num_channels == 2:
                    data = data[0::2]
            else:
                data = [0] * num_samples

            rms_values = []
            max_rms = 1.0

            for f in range(total_frames):
                start = f * samples_per_frame
                end = min(len(data), start + samples_per_frame)
                chunk = data[start:end]
                if chunk:
                    sq_sum = sum(float(x) ** 2 for x in chunk)
                    rms = math.sqrt(sq_sum / len(chunk))
                else:
                    rms = 0.0
                rms_values.append(rms)
                if rms > max_rms:
                    max_rms = rms

            normalized = [round(val / max_rms, 3) for val in rms_values]
            return normalized, round(duration, 2)

        except Exception:
            duration = 3.0
            num_frames = int(duration * fps)
            return [0.3] * num_frames, duration

    def _generate_avatar_sprite(self, cue: str, mouth_state: str) -> Image.Image:
        """Procedurally render a stylized, high-res AI Teacher avatar with cue & mouth state."""
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        cx, cy = self.width // 2, self.height // 2 + 20

        body_box = [cx - 160, cy + 80, cx + 160, self.height + 40]
        draw.chord(body_box, 180, 360, fill=(30, 41, 59, 255), outline=(15, 23, 42, 255), width=3)
        draw.polygon([(cx - 30, cy + 90), (cx, cy + 140), (cx + 30, cy + 90)], fill=(241, 245, 249, 255))
        draw.polygon([(cx - 8, cy + 120), (cx + 8, cy + 120), (cx, cy + 180)], fill=(13, 148, 136, 255))

        draw.rectangle([cx - 28, cy + 45, cx + 28, cy + 95], fill=(253, 224, 188, 255))

        head_cx = cx
        head_cy = cy
        if cue == "questioning":
            head_cx += 6
            head_cy -= 4

        draw.ellipse(
            [head_cx - 75, head_cy - 90, head_cx + 75, head_cy + 65],
            fill=(254, 235, 212, 255),
            outline=(224, 178, 140, 255),
            width=2,
        )

        draw.chord(
            [head_cx - 85, head_cy - 120, head_cx + 85, head_cy + 10],
            170,
            370,
            fill=(45, 30, 25, 255),
            outline=(30, 20, 15, 255),
            width=2,
        )
        draw.ellipse([head_cx - 82, head_cy - 80, head_cx - 65, head_cy - 20], fill=(45, 30, 25, 255))
        draw.ellipse([head_cx + 65, head_cy - 80, head_cx + 82, head_cy - 20], fill=(45, 30, 25, 255))

        left_brow_y = head_cy - 35
        right_brow_y = head_cy - 35
        if cue == "emphasis":
            left_brow_y -= 8
            right_brow_y -= 8
        elif cue == "questioning":
            right_brow_y -= 12

        draw.line([(head_cx - 45, left_brow_y), (head_cx - 15, left_brow_y + 2)], fill=(45, 30, 25, 255), width=4)
        draw.line([(head_cx + 15, right_brow_y + 2), (head_cx + 45, right_brow_y)], fill=(45, 30, 25, 255), width=4)

        draw.rounded_rectangle(
            [head_cx - 52, head_cy - 26, head_cx - 10, head_cy + 4], radius=6, outline=(15, 23, 42, 255), width=3
        )
        draw.rounded_rectangle(
            [head_cx + 10, head_cy - 26, head_cx + 52, head_cy + 4], radius=6, outline=(15, 23, 42, 255), width=3
        )
        draw.line([(head_cx - 10, head_cy - 11), (head_cx + 10, head_cy - 11)], fill=(15, 23, 42, 255), width=3)

        draw.ellipse([head_cx - 35, head_cy - 16, head_cx - 27, head_cy - 8], fill=(30, 41, 59, 255))
        draw.ellipse([head_cx + 27, head_cy - 16, head_cx + 35, head_cy - 8], fill=(30, 41, 59, 255))
        draw.ellipse([head_cx - 34, head_cy - 15, head_cx - 31, head_cy - 12], fill=(255, 255, 255, 255))
        draw.ellipse([head_cx + 28, head_cy - 15, head_cx + 31, head_cy - 12], fill=(255, 255, 255, 255))

        draw.line([(head_cx, head_cy - 5), (head_cx - 4, head_cy + 15)], fill=(210, 160, 120, 255), width=2)
        draw.line([(head_cx - 4, head_cy + 15), (head_cx + 4, head_cy + 15)], fill=(210, 160, 120, 255), width=2)

        mouth_y = head_cy + 35
        if mouth_state == "closed":
            draw.line([(head_cx - 18, mouth_y), (head_cx + 18, mouth_y)], fill=(185, 28, 28, 255), width=3)
            draw.arc([head_cx - 18, mouth_y - 4, head_cx + 18, mouth_y + 6], 0, 180, fill=(185, 28, 28, 255), width=2)
        elif mouth_state == "half_open":
            draw.ellipse(
                [head_cx - 14, mouth_y - 5, head_cx + 14, mouth_y + 9],
                fill=(127, 29, 29, 255),
                outline=(185, 28, 28, 255),
                width=2,
            )
            draw.rectangle([head_cx - 10, mouth_y - 4, head_cx + 10, mouth_y], fill=(255, 255, 255, 255))
        elif mouth_state == "open":
            draw.ellipse(
                [head_cx - 16, mouth_y - 8, head_cx + 16, mouth_y + 14],
                fill=(127, 29, 29, 255),
                outline=(185, 28, 28, 255),
                width=2,
            )
            draw.rectangle([head_cx - 12, mouth_y - 7, head_cx + 12, mouth_y - 1], fill=(255, 255, 255, 255))
            draw.chord([head_cx - 10, mouth_y + 4, head_cx + 10, mouth_y + 13], 0, 180, fill=(244, 63, 94, 255))

        return img
