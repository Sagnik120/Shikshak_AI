"""
Shikshak AI - avatar_voice module root exports.
"""

from modules.avatar_voice.src import (
    AvatarVoiceService,
    RenderedVideoSegment,
    TeachingSegment,
    VisualSpec,
)

__all__ = [
    "AvatarVoiceService",
    "TeachingSegment",
    "RenderedVideoSegment",
    "VisualSpec",
]
