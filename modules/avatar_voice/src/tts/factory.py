"""
TTS Factory providing automatic failover across TTS engines.
"""

import logging
from typing import Optional
from modules.avatar_voice.src.models import TTSResult
from modules.avatar_voice.src.tts.base import TTSAdapter, resolve_voice_id
from modules.avatar_voice.src.tts.edge_tts_adapter import EdgeTTSAdapter
from modules.avatar_voice.src.tts.fallback_adapter import FallbackTTSAdapter

logger = logging.getLogger(__name__)


class ResilientTTSAdapter:
    """Combines EdgeTTSAdapter with automatic FallbackTTSAdapter failover."""

    def __init__(self, output_dir: Optional[str] = None):
        self.edge_adapter = EdgeTTSAdapter(output_dir=output_dir)
        self.fallback_adapter = FallbackTTSAdapter(output_dir=output_dir)

    def synthesize(
        self,
        text: str,
        language: str = "en",
        voice_id: Optional[str] = None,
        avatar_cue: str = "neutral"
    ) -> TTSResult:
        """Synthesize text to speech with automatic fallback on network or driver error."""
        voice = voice_id or resolve_voice_id(language)
        try:
            return self.edge_adapter.synthesize(
                text=text, language=language, voice_id=voice, avatar_cue=avatar_cue
            )
        except Exception as e:
            logger.warning(f"Primary Edge-TTS failed ({e}). Cascading to FallbackTTSAdapter.")
            return self.fallback_adapter.synthesize(
                text=text, language=language, voice_id=voice, avatar_cue=avatar_cue
            )


class TTSFactory:
    """Factory for obtaining configured TTS adapters."""

    @staticmethod
    def get_adapter(engine: str = "resilient", output_dir: Optional[str] = None) -> TTSAdapter:
        if engine == "edge-tts":
            return EdgeTTSAdapter(output_dir=output_dir)
        elif engine == "fallback":
            return FallbackTTSAdapter(output_dir=output_dir)
        return ResilientTTSAdapter(output_dir=output_dir)
