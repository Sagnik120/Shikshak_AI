"""
Edge-TTS Adapter utilizing Microsoft Edge cloud neural voices.
Provides high-fidelity multilingual synthesis with zero API keys and native WebVTT export.
"""

import asyncio
import os
import subprocess
import tempfile
import uuid
from typing import List, Optional
from modules.avatar_voice.src.models import TTSResult, WordTimestamp
from modules.avatar_voice.src.tts.base import resolve_voice_id


# Cue-to-Prosody mapping per Round 2 Design (Issue 4)
CUE_PROSODY = {
    "neutral":     {"rate": "+0%",  "pitch": "+0Hz"},
    "emphasis":    {"rate": "-8%",  "pitch": "+15Hz"},   # slower, slightly higher = deliberate stress
    "questioning": {"rate": "+0%",  "pitch": "+25Hz"},   # rising pitch = question intonation
    "encouraging": {"rate": "+4%",  "pitch": "+15Hz"},   # upbeat, warm
    "celebratory": {"rate": "+6%",  "pitch": "+20Hz"},   # enthusiastic praise
}


class EdgeTTSAdapter:
    """Primary TTS adapter wrapping edge-tts with WebVTT subtitle, word timestamp extraction, and cue prosody."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(tempfile.gettempdir(), "shikshak_tts")
        os.makedirs(self.output_dir, exist_ok=True)

    async def _synthesize_async(self, text: str, voice_id: str, avatar_cue: str = "neutral") -> TTSResult:
        import edge_tts

        session_id = uuid.uuid4().hex[:8]
        mp3_path = os.path.join(self.output_dir, f"tts_{session_id}.mp3")
        wav_path = os.path.join(self.output_dir, f"tts_{session_id}.wav")
        vtt_path = os.path.join(self.output_dir, f"captions_{session_id}.vtt")

        # Resolve cue prosody (rate & pitch)
        cue_key = (avatar_cue or "neutral").strip().lower()
        prosody = CUE_PROSODY.get(cue_key, CUE_PROSODY["neutral"])
        rate = prosody["rate"]
        pitch = prosody["pitch"]

        communicate = edge_tts.Communicate(text, voice_id, rate=rate, pitch=pitch)
        submaker = edge_tts.SubMaker()
        word_timestamps: List[WordTimestamp] = []

        with open(mp3_path, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)
                    offset_sec = chunk["offset"] / 10_000_000
                    duration_sec = chunk["duration"] / 10_000_000
                    word_timestamps.append(
                        WordTimestamp(
                            word=chunk["text"],
                            start_sec=round(offset_sec, 3),
                            end_sec=round(offset_sec + duration_sec, 3),
                        )
                    )

        # Write WebVTT captions
        content = submaker.get_srt()
        if "-->" not in content and word_timestamps:
            def _fmt(sec: float) -> str:
                m = int(sec // 60)
                s = int(sec % 60)
                ms = int((sec % 1) * 1000)
                return f"{m:02d}:{s:02d}.{ms:03d}"

            vtt_cues = ["WEBVTT\n"]
            chunk_sz = 4
            for i in range(0, len(word_timestamps), chunk_sz):
                c = word_timestamps[i : i + chunk_sz]
                start_s = _fmt(c[0].start_sec)
                end_s = _fmt(c[-1].end_sec)
                phrase = " ".join(w.word for w in c)
                vtt_cues.append(f"{start_s} --> {end_s}\n{phrase}\n")
            content = "\n".join(vtt_cues)
        elif not content.startswith("WEBVTT"):
            content = f"WEBVTT\n\n{content}"

        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Transcode MP3 to WAV 24kHz mono
        duration_sec = self._transcode_to_wav(mp3_path, wav_path)

        if duration_sec <= 0.0 and word_timestamps:
            duration_sec = max(w.end_sec for w in word_timestamps)
        elif duration_sec <= 0.0:
            duration_sec = max(1.0, len(text.split()) * 0.35)

        return TTSResult(
            audio_path=wav_path,
            duration_sec=round(duration_sec, 2),
            word_timestamps=word_timestamps,
            vtt_path=vtt_path,
            engine_used="edge-tts",
        )

    def _transcode_to_wav(self, mp3_path: str, wav_path: str) -> float:
        """Convert MP3 to 24kHz mono WAV and return audio duration using dual-path FFmpeg."""
        import shutil
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            try:
                import imageio_ffmpeg
                ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg_bin = None

        if ffmpeg_bin:
            try:
                subprocess.run(
                    [ffmpeg_bin, "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1", wav_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                import wave
                with wave.open(wav_path, "r") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    return frames / float(rate)
            except Exception:
                pass

        try:
            import wave
            with open(mp3_path, "rb") as f:
                data = f.read()
            est_duration = max(1.0, len(data) / 16000.0)
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(b"\x00" * int(24000 * 2 * est_duration))
            return est_duration
        except Exception:
            return 3.0

    def synthesize(
        self,
        text: str,
        language: str = "en",
        voice_id: Optional[str] = None,
        avatar_cue: str = "neutral"
    ) -> TTSResult:
        """Synchronous wrapper for synthesize with cue-driven prosody."""
        chosen_voice = voice_id or resolve_voice_id(language)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(
                self._synthesize_async(text, chosen_voice, avatar_cue=avatar_cue)
            )
        else:
            return loop.run_until_complete(
                self._synthesize_async(text, chosen_voice, avatar_cue=avatar_cue)
            )
