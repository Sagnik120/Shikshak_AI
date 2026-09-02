"""
Offline Fallback TTS Adapter.
Generates modulated acoustic waveforms, word-level timestamps, and WebVTT captions
purely in Python without external network or binary dependencies.
"""

import math
import os
import struct
import tempfile
import uuid
import wave
from typing import List, Optional
from modules.avatar_voice.src.models import TTSResult, WordTimestamp
from modules.avatar_voice.src.tts.base import resolve_voice_id


class FallbackTTSAdapter:
    """Zero-dependency offline acoustic synthesizer and caption generator."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(tempfile.gettempdir(), "shikshak_tts")
        os.makedirs(self.output_dir, exist_ok=True)

    def synthesize(self, text: str, language: str = "en", voice_id: Optional[str] = None) -> TTSResult:
        """Generate audio and word timestamps for text offline."""
        chosen_voice = voice_id or resolve_voice_id(language)
        session_id = uuid.uuid4().hex[:8]
        wav_path = os.path.join(self.output_dir, f"fallback_tts_{session_id}.wav")
        vtt_path = os.path.join(self.output_dir, f"fallback_captions_{session_id}.vtt")

        words = [w.strip() for w in text.split() if w.strip()]
        if not words:
            words = ["..."]

        sample_rate = 24000
        word_timestamps: List[WordTimestamp] = []
        audio_samples: List[int] = []

        current_time = 0.0
        for idx, word in enumerate(words):
            word_duration = max(0.2, len(word) * 0.06 + 0.15)
            start_sec = current_time
            end_sec = current_time + word_duration
            word_timestamps.append(
                WordTimestamp(
                    word=word,
                    start_sec=round(start_sec, 3),
                    end_sec=round(end_sec, 3),
                )
            )

            num_samples = int(word_duration * sample_rate)
            base_freq = 220.0 if "madhur" in chosen_voice.lower() or "prabhat" in chosen_voice.lower() else 330.0

            for s_idx in range(num_samples):
                t = s_idx / sample_rate
                envelope = math.sin(math.pi * (s_idx / num_samples))
                sample_val = envelope * (
                    0.6 * math.sin(2 * math.pi * base_freq * t)
                    + 0.3 * math.sin(2 * math.pi * (base_freq * 1.5) * t)
                    + 0.1 * math.sin(2 * math.pi * (base_freq * 2.0) * t)
                )
                int_sample = int(sample_val * 32767 * 0.7)
                audio_samples.append(max(-32768, min(32767, int_sample)))

            pause_samples = int(0.05 * sample_rate)
            audio_samples.extend([0] * pause_samples)
            current_time = end_sec + 0.05

        total_duration = round(current_time, 2)

        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            raw_data = struct.pack(f"<{len(audio_samples)}h", *audio_samples)
            wf.writeframes(raw_data)

        self._write_vtt(vtt_path, word_timestamps)

        return TTSResult(
            audio_path=wav_path,
            duration_sec=total_duration,
            word_timestamps=word_timestamps,
            vtt_path=vtt_path,
            engine_used="fallback-offline",
        )

    def _write_vtt(self, vtt_path: str, word_timestamps: List[WordTimestamp]) -> None:
        """Write standard WebVTT file with grouped captions."""
        lines = ["WEBVTT", ""]
        chunk_size = 5
        for i in range(0, len(word_timestamps), chunk_size):
            chunk = word_timestamps[i : i + chunk_size]
            start_str = self._format_vtt_time(chunk[0].start_sec)
            end_str = self._format_vtt_time(chunk[-1].end_sec)
            phrase = " ".join(w.word for w in chunk)
            lines.append(f"{start_str} --> {end_str}")
            lines.append(phrase)
            lines.append("")

        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    def _format_vtt_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{mins:02d}:{secs:02d}.{millis:03d}"
