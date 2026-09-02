"""
Base interfaces and protocols for Avatar generation.
Strictly conforms to Contract.md §14 (AvatarAdapter).
"""

from typing import Protocol
from modules.avatar_voice.src.models import AvatarRenderResult


class AvatarAdapter(Protocol):
    """Protocol for Avatar Rendering per Contract §14."""

    def render(
        self, script_text: str, language: str, avatar_cue: str, audio_path: str
    ) -> AvatarRenderResult:
        """Render synchronized talking-head video/frame sequence from audio and cues."""
        ...
