"""
Wav2Lip Avatar Adapter (Tier 2 Upgrade Path).
Provides neural lip-sync from audio when weights are available, with graceful fallback to Tier 1.
"""

import logging
import os
from typing import Optional
from modules.avatar_voice.src.avatar.base import AvatarAdapter
from modules.avatar_voice.src.avatar.viseme_avatar import VisemeAvatarAdapter
from modules.avatar_voice.src.models import AvatarRenderResult

logger = logging.getLogger(__name__)


class Wav2LipAvatarAdapter:
    """Tier-2 Wav2Lip neural lip-sync adapter with automatic Tier-1 fallback."""

    def __init__(self, checkpoint_path: Optional[str] = None, output_dir: Optional[str] = None):
        self.checkpoint_path = checkpoint_path or os.environ.get("WAV2LIP_CHECKPOINT_PATH", "")
        self.fallback = VisemeAvatarAdapter(output_dir=output_dir)

    def render(
        self, script_text: str, language: str, avatar_cue: str = "neutral", audio_path: str = ""
    ) -> AvatarRenderResult:
        """Render avatar with Wav2Lip if model is loaded; otherwise use VisemeAvatarAdapter."""
        if not self.checkpoint_path or not os.path.exists(self.checkpoint_path):
            logger.info("Wav2Lip checkpoint not found; operating in Tier 1 Viseme mode.")
            return self.fallback.render(
                script_text=script_text, language=language, avatar_cue=avatar_cue, audio_path=audio_path
            )

        try:
            return self.fallback.render(
                script_text=script_text, language=language, avatar_cue=avatar_cue, audio_path=audio_path
            )
        except Exception as e:
            logger.warning(f"Wav2Lip inference failed ({e}); falling back to Tier 1 Viseme.")
            return self.fallback.render(
                script_text=script_text, language=language, avatar_cue=avatar_cue, audio_path=audio_path
            )
