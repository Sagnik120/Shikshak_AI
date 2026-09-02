"""
Avatar & Voice Module package exports.
"""

from modules.avatar_voice.src.avatar import AvatarAdapter, VisemeAvatarAdapter, Wav2LipAvatarAdapter
from modules.avatar_voice.src.compositor import FFmpegCompositor
from modules.avatar_voice.src.models import (
    AvatarRenderResult,
    RenderJobStatus,
    RenderedVideoSegment,
    TeachingSegment,
    TTSResult,
    VisualRenderResult,
    VisualSpec,
    WordTimestamp,
)
from modules.avatar_voice.src.service import AvatarVoiceService
from modules.avatar_voice.src.tts import (
    EdgeTTSAdapter,
    FallbackTTSAdapter,
    ResilientTTSAdapter,
    TTSAdapter,
    TTSFactory,
    VOICE_CATALOG,
    resolve_voice_id,
)
from modules.avatar_voice.src.visuals import (
    BaseRenderer,
    CodeRenderer,
    DiagramRenderer,
    EquationRenderer,
    GraphRenderer,
    ImageRenderer,
    MapRenderer,
    THEME,
    TimelineRenderer,
    VisualRenderer,
    VisualRendererFactory,
)

__all__ = [
    # Models
    "VisualSpec",
    "TeachingSegment",
    "RenderedVideoSegment",
    "TTSResult",
    "WordTimestamp",
    "AvatarRenderResult",
    "VisualRenderResult",
    "RenderJobStatus",
    # Service Facade
    "AvatarVoiceService",
    # TTS
    "TTSAdapter",
    "VOICE_CATALOG",
    "resolve_voice_id",
    "EdgeTTSAdapter",
    "FallbackTTSAdapter",
    "ResilientTTSAdapter",
    "TTSFactory",
    # Avatar
    "AvatarAdapter",
    "VisemeAvatarAdapter",
    "Wav2LipAvatarAdapter",
    # Visuals
    "VisualRenderer",
    "BaseRenderer",
    "THEME",
    "EquationRenderer",
    "GraphRenderer",
    "DiagramRenderer",
    "CodeRenderer",
    "TimelineRenderer",
    "MapRenderer",
    "ImageRenderer",
    "VisualRendererFactory",
    # Compositor
    "FFmpegCompositor",
]
