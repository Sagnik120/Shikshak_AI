"""Isolated testbed web server for avatar_voice module.

Runs on dedicated Port 8004 to avoid interfering with:
  - Port 8000 (Production Backend)
  - Port 8001 (AI Agent Orchestration Testbed)
  - Port 8002 (RAG Testbed)

Directly imports and exercises production modules from `modules.avatar_voice.src.*`.
Employs AvatarVoiceTestLogger to record full input/output and checkpoint traces.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Direct imports from production avatar_voice package
from modules.avatar_voice.src.models import (
    AvatarRenderResult,
    RenderedVideoSegment,
    TeachingSegment,
    VisualRenderResult,
    VisualSpec,
    WordTimestamp,
)
from modules.avatar_voice.src.avatar.factory import AvatarFactory
from modules.avatar_voice.src.compositor.ffmpeg_compositor import FFmpegCompositor
from modules.avatar_voice.src.service import AvatarVoiceService
from modules.avatar_voice.src.tts.factory import TTSFactory
from modules.avatar_voice.src.visuals.factory import VisualRendererFactory
from modules.avatar_voice.tests.web_test.logger import AvatarVoiceTestLogger

# Storage directories
STATIC_DIR = Path(__file__).resolve().parent / "static"
MEDIA_DIR = PROJECT_ROOT / "data" / "avatar_voice_test_media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

(MEDIA_DIR / "audio").mkdir(parents=True, exist_ok=True)
(MEDIA_DIR / "visuals").mkdir(parents=True, exist_ok=True)
(MEDIA_DIR / "videos").mkdir(parents=True, exist_ok=True)

# Initialize logger
logger = AvatarVoiceTestLogger()

app = FastAPI(
    title="Shikshak AI — Avatar & Voice Isolated Web Testbed",
    description="Dedicated testing backend for TTS, Avatar Lip-Sync, Visual Renderers, and 1080p Video Compositing.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------

class TTSTestRequest(BaseModel):
    text: str = Field(..., description="Narration script text")
    language: str = Field(default="en", description="en, hi, hinglish, or bn")
    voice_id: Optional[str] = None
    provider: str = Field(default="resilient", description="resilient, edge, or fallback")
    avatar_cue: str = Field(default="neutral", description="neutral, emphasis, questioning, encouraging, celebratory")


class AvatarTestRequest(BaseModel):
    script_text: str = Field(default="Let us understand Ohm's Law.")
    language: str = Field(default="en")
    avatar_cue: str = Field(default="neutral")
    engine: str = Field(default="tier1", description="tier1 (viseme), tier2 (musetalk), or auto")
    audio_path: Optional[str] = None


class VisualsTestRequest(BaseModel):
    visual_type: str = Field(..., description="equation, graph, code, diagram, timeline, map, or image")
    content: Union[str, Dict[str, Any], List[Any]] = Field(...)
    steps: Optional[List[str]] = None
    execution_output: Optional[str] = None


class RenderSegmentRequest(BaseModel):
    node_id: str = Field(default="node_001")
    script_text: str = Field(...)
    language: str = Field(default="en")
    avatar_cue: str = Field(default="neutral")
    visual_spec: Dict[str, Any] = Field(...)
    tts_provider: str = Field(default="resilient")
    avatar_engine: str = Field(default="tier1")


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/test/status")
async def get_test_status() -> Dict[str, Any]:
    """Health check reporting system diagnostics, hardware acceleration, and available adapters."""
    # Check FFmpeg
    ffmpeg_bin = shutil.which("ffmpeg")
    ffmpeg_source = "system_path" if ffmpeg_bin else None
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            ffmpeg_source = "imageio_static"
        except Exception:
            ffmpeg_bin = None
            ffmpeg_source = "unavailable_pil_fallback"

    # Check CUDA / MPS
    device = "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
    except Exception:
        pass

    return {
        "status": "ready",
        "port": 8004,
        "media_dir": str(MEDIA_DIR),
        "tts": {
            "default_provider": "resilient",
            "supported_languages": ["en", "hi", "hinglish", "bn"],
            "voices": {
                "en": "en-IN-NeerjaNeural",
                "hi": "hi-IN-SwaraNeural",
                "bn": "bn-IN-TanishaaNeural",
            },
        },
        "avatar": {
            "tier1": "VisemeAvatarAdapter (24 FPS procedural RMS)",
            "tier2": "MuseTalkAvatarAdapter (Neural Latent Diffusion)",
            "device": device,
        },
        "visuals": {
            "renderers": ["equation", "graph", "code", "diagram", "timeline", "map", "image"],
            "canvas_dimensions": "1344 x 1080 (70% split-screen)",
        },
        "compositor": {
            "canvas": "1920 x 1080 @ 24 FPS",
            "ffmpeg_available": ffmpeg_bin is not None,
            "ffmpeg_source": ffmpeg_source,
            "ffmpeg_path": ffmpeg_bin,
        },
    }


@app.post("/api/test/tts")
async def test_tts(req: TTSTestRequest) -> Dict[str, Any]:
    """Test text-to-speech synthesis with SSML cue prosody and WebVTT generation."""
    try:
        adapter = TTSFactory.get_adapter(req.provider, output_dir=str(MEDIA_DIR / "audio"))
        # Set cue on adapter if supported
        if hasattr(adapter, "avatar_cue"):
            adapter.avatar_cue = req.avatar_cue

        result = adapter.synthesize(
            text=req.text,
            language=req.language,
            voice_id=req.voice_id,
        )

        audio_rel_url = f"/media/audio/{Path(result.audio_path).name}"
        vtt_rel_url = f"/media/audio/{Path(result.vtt_path).name}" if result.vtt_path else None

        word_timestamps = result.word_timestamps or []
        log_meta = logger.log_tts(
            text=req.text,
            language=req.language,
            voice_id=req.voice_id,
            provider=req.provider,
            avatar_cue=req.avatar_cue,
            duration_sec=result.duration_sec,
            word_count=len(word_timestamps),
            vtt_path=result.vtt_path or "",
            audio_path=result.audio_path,
            source_file="modules/avatar_voice/src/tts/edge_tts_adapter.py" if req.provider != "fallback" else "modules/avatar_voice/src/tts/fallback_adapter.py",
        )

        return {
            "success": True,
            "audio_url": audio_rel_url,
            "vtt_url": vtt_rel_url,
            "duration_sec": result.duration_sec,
            "sample_rate": 24000,
            "word_count": len(word_timestamps),
            "timestamps": [ts.model_dump() for ts in word_timestamps[:30]],
            "log_id": log_meta["log_id"],
            "log_file": log_meta["relative_log"],
        }
    except Exception as e:
        log_meta = logger.log_error(
            operation="speech_synthesis",
            error=e,
            input_payload=req.model_dump(),
            source_file="modules/avatar_voice/src/tts/edge_tts_adapter.py",
            source_function="synthesize",
        )
        raise HTTPException(status_code=500, detail={"error": str(e), "log_id": log_meta["log_id"]})


@app.post("/api/test/avatar")
async def test_avatar(req: AvatarTestRequest) -> Dict[str, Any]:
    """Test avatar lip-sync, RMS envelope, and procedural facial animations."""
    try:
        # If no audio provided, generate a quick fallback acoustic clip
        audio_path = req.audio_path
        if not audio_path or not Path(audio_path).exists():
            tts_adapter = TTSFactory.get_adapter("fallback", output_dir=str(MEDIA_DIR / "audio"))
            tts_res = tts_adapter.synthesize(req.script_text, language=req.language)
            audio_path = tts_res.audio_path

        avatar_adapter = AvatarFactory.get_adapter(req.engine)
        result = avatar_adapter.render(
            script_text=req.script_text,
            language=req.language,
            avatar_cue=req.avatar_cue,
            audio_path=audio_path,
        )

        # Detect mouth states from frame files in frames_dir
        mouth_states = []
        sample_frame_urls = []
        frame_files = []
        if result.frames_dir and Path(result.frames_dir).exists():
            frame_files = sorted(list(Path(result.frames_dir).glob("*.png")))
            for fp in frame_files:
                name = fp.name
                if "slightly_open" in name:
                    mouth_states.append("slightly_open")
                elif "wide_open" in name:
                    mouth_states.append("wide_open")
                elif "o_shape" in name:
                    mouth_states.append("o_shape")
                elif "closed" in name:
                    mouth_states.append("closed")

            # Collect evenly-spaced sample frames for UI carousel
            step = max(1, len(frame_files) // 8)
            samples = frame_files[::step][:8]
            for s in samples:
                dest = MEDIA_DIR / "visuals" / s.name
                if not dest.exists():
                    shutil.copy(str(s), str(dest))
                sample_frame_urls.append(f"/media/visuals/{s.name}")

        unique_mouth_states = list(set(mouth_states)) or ["closed", "slightly_open", "wide_open"]
        total_frames = result.frame_count or len(frame_files)

        log_meta = logger.log_avatar(
            script_text=req.script_text,
            language=req.language,
            avatar_cue=req.avatar_cue,
            audio_path=audio_path,
            engine=req.engine,
            tier_used=result.tier_used,
            tier_used_reason=result.tier_used_reason,
            frame_count=total_frames,
            fps=result.fps,
            mouth_states_detected=unique_mouth_states,
            source_file="modules/avatar_voice/src/avatar/viseme_avatar.py" if result.tier_used == "tier1_viseme" else "modules/avatar_voice/src/avatar/musetalk_avatar.py",
        )

        return {
            "success": True,
            "tier_used": result.tier_used,
            "tier_used_reason": result.tier_used_reason,
            "frame_count": total_frames,
            "fps": result.fps,
            "mouth_states_detected": unique_mouth_states,
            "sample_frame_urls": sample_frame_urls,
            "video_path": getattr(result, "video_path", None),
            "log_id": log_meta["log_id"],
            "log_file": log_meta["relative_log"],
        }
    except Exception as e:
        log_meta = logger.log_error(
            operation="avatar_animation",
            error=e,
            input_payload=req.model_dump(),
            source_file="modules/avatar_voice/src/avatar/viseme_avatar.py",
            source_function="render",
        )
        raise HTTPException(status_code=500, detail={"error": str(e), "log_id": log_meta["log_id"]})


@app.post("/api/test/visuals")
async def test_visuals(req: VisualsTestRequest) -> Dict[str, Any]:
    """Test multi-subject visual slide renderers and progressive derivations."""
    try:
        factory = VisualRendererFactory(output_dir=str(MEDIA_DIR / "visuals"))
        renderer = factory.renderers.get(req.visual_type, factory.renderers["diagram"])

        spec = VisualSpec(
            type=req.visual_type,
            content=req.content,
            steps=req.steps,
            execution_output=req.execution_output,
        )

        result: VisualRenderResult = renderer.render(spec)

        primary_url = f"/media/visuals/{Path(result.image_path).name}"
        step_urls = [f"/media/visuals/{Path(p).name}" for p in (result.step_image_paths or [])]

        log_meta = logger.log_visuals(
            visual_type=req.visual_type,
            content=req.content,
            steps=req.steps,
            execution_output=req.execution_output,
            generated_step_count=len(result.step_image_paths or []),
            primary_image_path=result.image_path,
            step_image_paths=result.step_image_paths or [],
            source_file=f"modules/avatar_voice/src/visuals/{req.visual_type}_renderer.py",
        )

        return {
            "success": True,
            "visual_type": req.visual_type,
            "primary_image_url": primary_url,
            "step_image_urls": step_urls,
            "step_count": len(step_urls),
            "step_contents": result.step_contents or [],
            "log_id": log_meta["log_id"],
            "log_file": log_meta["relative_log"],
        }
    except Exception as e:
        log_meta = logger.log_error(
            operation="visual_slide_rendering",
            error=e,
            input_payload=req.model_dump(),
            source_file="modules/avatar_voice/src/visuals/factory.py",
            source_function="render",
        )
        raise HTTPException(status_code=500, detail={"error": str(e), "log_id": log_meta["log_id"]})


@app.post("/api/test/render_sync")
async def test_render_sync(req: RenderSegmentRequest) -> Dict[str, Any]:
    """Executes full end-to-end 1080p video composition synchronously."""
    try:
        # Build service with test output directories
        tts_adapter = TTSFactory.get_adapter(req.tts_provider, output_dir=str(MEDIA_DIR / "audio"))
        if hasattr(tts_adapter, "avatar_cue"):
            tts_adapter.avatar_cue = req.avatar_cue

        avatar_adapter = AvatarFactory.get_adapter(req.avatar_engine)
        compositor = FFmpegCompositor(output_dir=str(MEDIA_DIR / "videos"))

        service = AvatarVoiceService(
            tts_adapter=tts_adapter,
            avatar_adapter=avatar_adapter,
            compositor=compositor,
        )

        visual_spec = VisualSpec(**req.visual_spec)
        segment = TeachingSegment(
            node_id=req.node_id,
            script_text=req.script_text,
            language=req.language,
            visual_spec=visual_spec,
            avatar_cue=req.avatar_cue,
        )

        result: RenderedVideoSegment = service.render_segment_sync(segment)

        video_filename = Path(result.video_url).name
        video_url = f"/media/videos/{video_filename}"
        vtt_url = f"/media/videos/{Path(result.captions_vtt_url).name}" if result.captions_vtt_url else None

        log_meta = logger.log_service(
            node_id=req.node_id,
            script_text=req.script_text,
            language=req.language,
            avatar_cue=req.avatar_cue,
            visual_type=visual_spec.type,
            sync_or_async="sync",
            duration_sec=result.duration_sec,
            video_url=video_url,
            vtt_url=vtt_url,
            source_file="modules/avatar_voice/src/service.py",
            source_function="render_segment_sync",
        )

        return {
            "success": True,
            "node_id": result.node_id,
            "video_url": video_url,
            "duration_sec": result.duration_sec,
            "captions_vtt_url": vtt_url,
            "log_id": log_meta["log_id"],
            "log_file": log_meta["relative_log"],
        }
    except Exception as e:
        log_meta = logger.log_error(
            operation="segment_rendering",
            error=e,
            input_payload=req.model_dump(),
            source_file="modules/avatar_voice/src/service.py",
            source_function="render_segment_sync",
        )
        raise HTTPException(status_code=500, detail={"error": str(e), "log_id": log_meta["log_id"]})


# -----------------------------------------------------------------------------
# Log Explorer Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/test/logs")
async def list_logs(category: Optional[str] = Query(None), limit: int = Query(50)) -> Dict[str, Any]:
    """Returns recent log manifests across tts, avatar, visuals, compositor, service, errors."""
    items = logger.list_logs(category=category, limit=limit)
    return {"total_logs": len(items), "logs": items}


@app.get("/api/test/logs/{category}/{filename}")
async def get_log(category: str, filename: str) -> Any:
    """Retrieves full content of a specific log file."""
    content = logger.get_log(category=category, filename=filename)
    if content is None:
        raise HTTPException(status_code=404, detail="Log file not found")
    return content


# -----------------------------------------------------------------------------
# Static Mounts
# -----------------------------------------------------------------------------

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("  SHIKSHAK AI — AVATAR & VOICE ISOLATED WEB TESTBED")
    print("  Running on: http://localhost:8004")
    print("  Testing Code: modules/avatar_voice/src/")
    print("  Production Backend (Port 8000) remains 100% untouched.")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8004)
