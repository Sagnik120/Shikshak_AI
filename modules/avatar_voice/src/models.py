"""
Pydantic data models and schemas for the avatar_voice module.
Strictly adheres to Contract.md §6 (TeachingSegment) and §7 (RenderedVideoSegment).
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class VisualSpec(BaseModel):
    """Specification for the visual aid on screen."""
    type: str = Field(..., description="equation|graph|diagram|code|image|timeline|map|simulation")
    content: Union[str, Dict[str, Any], List[Any]] = Field(
        ..., description="LaTeX, structured JSON, code snippet, prompt, or coordinates"
    )
    steps: Optional[List[str]] = Field(
        default=None,
        description="Optional ordered sequence of progressive steps (e.g. math derivations, line-by-line reveals)"
    )
    execution_output: Optional[str] = Field(
        default=None,
        description="Optional terminal/simulation execution output to display in an active output pane"
    )


class TeachingSegment(BaseModel):
    """
    Contract §6: AI Orchestration -> Avatar/Voice
    Input defining what the teacher avatar says and what visual to display.
    """
    node_id: str = Field(..., description="Unique node ID in the lesson graph")
    script_text: str = Field(..., description="The spoken narration script")
    language: str = Field(default="en", description="Language code e.g. en, hi, Hinglish")
    visual_spec: VisualSpec = Field(..., description="Specification of the on-screen visual aid")
    avatar_cue: Literal["neutral", "emphasis", "questioning"] = Field(
        default="neutral", description="Facial and pose cue for the avatar"
    )


class RenderedVideoSegment(BaseModel):
    """
    Contract §7: Avatar/Voice -> Backend/Frontend
    Output representing the fully rendered video segment with synchronized voice, visuals, and captions.
    """
    node_id: str = Field(..., description="Matches the TeachingSegment node_id")
    video_url: str = Field(..., description="Local file path or URL to the rendered MP4 video")
    duration_sec: float = Field(..., ge=0.0, description="Exact duration in seconds verified from audio/video")
    captions_vtt_url: Optional[str] = Field(
        default=None, description="Path or URL to the standalone WebVTT subtitle track"
    )


# Internal domain models (not cross-module contract schemas)

class WordTimestamp(BaseModel):
    """Word or sentence boundary timestamp for caption and animation sync."""
    word: str
    start_sec: float
    end_sec: float


class TTSResult(BaseModel):
    """Result of the text-to-speech synthesis stage."""
    audio_path: str
    duration_sec: float
    word_timestamps: List[WordTimestamp] = Field(default_factory=list)
    vtt_path: Optional[str] = None
    engine_used: str = "edge-tts"


class AvatarRenderResult(BaseModel):
    """Result of the avatar talking-head frame generation stage."""
    frames_dir: str
    frame_count: int
    fps: int = 24
    duration_sec: float
    is_transparent: bool = True
    tier: str = "tier1_viseme"


class VisualRenderResult(BaseModel):
    """Result of the visual panel synthesis stage."""
    image_path: str
    width: int = 1344
    height: int = 1080
    visual_type: str
    step_image_paths: List[str] = Field(
        default_factory=list,
        description="Ordered paths of progressive visual step frames"
    )
    is_progressive: bool = False


class RenderJobStatus(BaseModel):
    """Internal job status tracking for non-blocking async rendering."""
    job_id: str
    status: Literal["queued", "rendering", "done", "failed"] = "queued"
    progress_pct: float = 0.0
    stage: str = "initialized"
    result: Optional[RenderedVideoSegment] = None
    error: Optional[str] = None
