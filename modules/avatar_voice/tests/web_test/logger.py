"""Structured, hierarchical logging engine for avatar_voice module isolated testing.

Manages fine-grained JSON manifests and human-readable text logs categorized by:
  - tts/          (Speech synthesis, neural voices, SSML prosody, language pacing)
  - avatar/       (RMS audio envelopes, viseme mouth stages, eye blinks, cue poses)
  - visuals/      (Multi-subject slide rendering, progressive math derivations, code consoles)
  - compositor/   (FFmpeg filter graphs, visual concat sequencing, 1080p video encoding)
  - service/      (End-to-end sync and async job queue lifecycles)
  - errors/       (Exceptions, fallback triggers, and hardware diagnostics)

Explicitly logs the exact source file and function name for full execution traceability.
"""

from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR = DEFAULT_LOGS_DIR


class AvatarVoiceTestLogger:
    """Thread-safe hierarchical logger for isolated avatar_voice testing."""

    CATEGORIES = ("tts", "avatar", "visuals", "compositor", "service", "errors")

    def __init__(self, base_log_dir: Optional[str] = None):
        if base_log_dir:
            self.base_dir = Path(base_log_dir)
        else:
            self.base_dir = DEFAULT_LOGS_DIR

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure all category subdirectories and .gitkeep files exist."""
        for cat in self.CATEGORIES:
            cat_dir = self.base_dir / cat
            cat_dir.mkdir(parents=True, exist_ok=True)
            gitkeep = cat_dir / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()

    def _generate_log_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def _get_timestamp_str(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _write_log(
        self,
        category: str,
        operation: str,
        source_file: str,
        source_function: str,
        status: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Writes both a structured JSON manifest and a formatted text .log file."""
        if category not in self.CATEGORIES:
            category = "errors"

        log_id = self._generate_log_id()
        timestamp = self._get_timestamp_str()
        iso_time = datetime.now().isoformat()

        base_filename = f"{timestamp}_{category}_{log_id}"
        json_path = self.base_dir / category / f"{base_filename}.json"
        text_path = self.base_dir / category / f"{base_filename}.log"

        payload = {
            "log_id": log_id,
            "timestamp": iso_time,
            "category": category,
            "operation": operation,
            "source": {
                "file": source_file,
                "function": source_function,
            },
            "source_file": source_file,
            "source_function": source_function,
            "status": status,
            "input": input_data,
            "checkpoints": checkpoints or [],
            "output": output_data,
            "error": error_details,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        lines = [
            "=" * 80,
            f"SHIKSHAK AI — AVATAR_VOICE TEST LOG: {log_id}",
            f"Category:     {category.upper()}",
            f"Operation:    {operation}",
            f"Status:       {status.upper()}",
            f"Source:       {source_file} :: {source_function}()",
            f"Timestamp:    {iso_time}",
            "=" * 80,
            "",
            "[INPUT PAYLOAD]",
            json.dumps(input_data, indent=2, ensure_ascii=False),
            "",
        ]

        if checkpoints:
            lines.append("[EXECUTION CHECKPOINTS]")
            for cp in checkpoints:
                ts = cp.get("time", "")
                name = cp.get("event", "checkpoint")
                details = cp.get("details", {})
                lines.append(f"-> [{ts}] {name}")
                lines.append(json.dumps(details, indent=2, ensure_ascii=False))
            lines.append("")

        if error_details:
            lines.append("[ERROR TRACE]")
            lines.append(json.dumps(error_details, indent=2, ensure_ascii=False))
            lines.append("")

        lines.append("[OUTPUT PAYLOAD]")
        lines.append(json.dumps(output_data, indent=2, ensure_ascii=False))
        lines.append("")

        with open(text_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return {
            "log_id": log_id,
            "json_path": str(json_path),
            "log_path": str(text_path),
            "relative_json": f"logs/{category}/{base_filename}.json",
            "relative_log": f"logs/{category}/{base_filename}.log",
            "source_file": source_file,
            "source_function": source_function,
        }

    # -------------------------------------------------------------------------
    # Specialized Logging Methods
    # -------------------------------------------------------------------------

    def log_tts(
        self,
        text: str,
        language: str,
        voice_id: Optional[str] = None,
        provider: str = "resilient",
        avatar_cue: str = "neutral",
        duration_sec: float = 0.0,
        word_count: int = 0,
        vtt_path: str = "",
        audio_path: str = "",
        status: str = "success",
        source_file: str = "modules/avatar_voice/src/tts/edge_tts_adapter.py",
        source_function: str = "synthesize",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs text-to-speech synthesis runs."""
        input_data = {
            "text": text,
            "language": language,
            "voice_id": voice_id,
            "provider": provider,
            "avatar_cue": avatar_cue,
        }
        output_data = {
            "duration_sec": duration_sec,
            "word_count": word_count,
            "audio_path": audio_path,
            "vtt_path": vtt_path,
            "status": status,
        }
        return self._write_log(
            category="tts",
            operation="speech_synthesis",
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_data,
            output_data=output_data,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_avatar(
        self,
        script_text: str,
        language: str,
        avatar_cue: str,
        audio_path: str,
        engine: str,
        tier_used: str,
        tier_used_reason: Optional[str],
        frame_count: int,
        fps: int,
        mouth_states_detected: List[str],
        status: str = "success",
        source_file: str = "modules/avatar_voice/src/avatar/viseme_avatar.py",
        source_function: str = "render",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs avatar frame and lip-sync generation."""
        input_data = {
            "script_text": script_text,
            "language": language,
            "avatar_cue": avatar_cue,
            "audio_path": audio_path,
            "requested_engine": engine,
        }
        output_data = {
            "tier_used": tier_used,
            "tier_used_reason": tier_used_reason,
            "frame_count": frame_count,
            "fps": fps,
            "mouth_states_detected": mouth_states_detected,
            "status": status,
        }
        return self._write_log(
            category="avatar",
            operation="avatar_animation",
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_data,
            output_data=output_data,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_visuals(
        self,
        visual_type: str,
        content: Any,
        steps: Optional[List[str]],
        execution_output: Optional[str],
        generated_step_count: int,
        primary_image_path: str,
        step_image_paths: List[str],
        status: str = "success",
        source_file: str = "modules/avatar_voice/src/visuals/factory.py",
        source_function: str = "render",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs multi-subject slide and progressive step rendering."""
        input_data = {
            "visual_type": visual_type,
            "content": content,
            "steps": steps,
            "execution_output": execution_output,
        }
        output_data = {
            "generated_step_count": generated_step_count,
            "primary_image_path": primary_image_path,
            "step_image_paths": step_image_paths,
            "status": status,
        }
        return self._write_log(
            category="visuals",
            operation="visual_slide_rendering",
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_data,
            output_data=output_data,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_compositor(
        self,
        visual_paths: List[str],
        avatar_frames: List[str],
        audio_path: str,
        vtt_path: Optional[str],
        duration_sec: float,
        output_video_path: str,
        ffmpeg_cmd: Optional[str],
        compositor_backend: str,  # 'ffmpeg' or 'pil_fallback'
        status: str = "success",
        source_file: str = "modules/avatar_voice/src/compositor/ffmpeg_compositor.py",
        source_function: str = "compose",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs 1080p Full HD video composition."""
        input_data = {
            "visual_paths_count": len(visual_paths),
            "avatar_frames_count": len(avatar_frames),
            "audio_path": audio_path,
            "vtt_path": vtt_path,
            "duration_sec": duration_sec,
        }
        output_data = {
            "output_video_path": output_video_path,
            "ffmpeg_cmd": ffmpeg_cmd,
            "compositor_backend": compositor_backend,
            "status": status,
        }
        return self._write_log(
            category="compositor",
            operation="video_composition",
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_data,
            output_data=output_data,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_service(
        self,
        node_id: str,
        script_text: str,
        language: str,
        avatar_cue: str,
        visual_type: str,
        sync_or_async: str,
        duration_sec: float,
        video_url: str,
        vtt_url: Optional[str],
        status: str = "success",
        source_file: str = "modules/avatar_voice/src/service.py",
        source_function: str = "render_segment_sync",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs unified service segment rendering."""
        input_data = {
            "node_id": node_id,
            "script_text": script_text,
            "language": language,
            "avatar_cue": avatar_cue,
            "visual_type": visual_type,
            "mode": sync_or_async,
        }
        output_data = {
            "duration_sec": duration_sec,
            "video_url": video_url,
            "vtt_url": vtt_url,
            "status": status,
        }
        return self._write_log(
            category="service",
            operation="segment_rendering",
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_data,
            output_data=output_data,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_error(
        self,
        operation: str,
        error: Exception,
        input_payload: Dict[str, Any],
        source_file: str,
        source_function: str,
    ) -> Dict[str, str]:
        """Logs unhandled exceptions and failures."""
        tb = traceback.format_exc()
        error_details = {
            "exception_type": type(error).__name__,
            "message": str(error),
            "traceback": tb,
        }
        return self._write_log(
            category="errors",
            operation=operation,
            source_file=source_file,
            source_function=source_function,
            status="error",
            input_data=input_payload,
            output_data={},
            error_details=error_details,
        )

    # -------------------------------------------------------------------------
    # Retrieval Methods for UI Explorer
    # -------------------------------------------------------------------------

    def list_logs(self, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recent log manifests for the web UI log explorer."""
        categories = [category] if category and category in self.CATEGORIES else self.CATEGORIES
        results = []

        for cat in categories:
            cat_dir = self.base_dir / cat
            if not cat_dir.exists():
                continue
            for json_file in sorted(cat_dir.glob("*.json"), reverse=True):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    results.append({
                        "log_id": meta.get("log_id"),
                        "timestamp": meta.get("timestamp"),
                        "category": meta.get("category"),
                        "operation": meta.get("operation"),
                        "status": meta.get("status"),
                        "source_file": meta.get("source", {}).get("file"),
                        "source_function": meta.get("source", {}).get("function"),
                        "filename": json_file.name,
                        "log_filename": json_file.with_suffix(".log").name,
                    })
                except Exception:
                    continue

        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]

    def get_log(self, category: str, filename: str) -> Optional[Dict[str, Any]]:
        """Retrieves raw JSON or parsed content of a specific log file."""
        if category not in self.CATEGORIES:
            return None

        # Prevent directory traversal
        safe_name = Path(filename).name
        target = self.base_dir / category / safe_name
        if not target.exists():
            return None

        if target.suffix == ".json":
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        elif target.suffix == ".log":
            with open(target, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        return None
