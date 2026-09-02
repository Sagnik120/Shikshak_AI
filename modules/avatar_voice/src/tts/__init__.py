"""
TTS Subsystem package exports.
"""

from modules.avatar_voice.src.tts.base import TTSAdapter, VOICE_CATALOG, resolve_voice_id
from modules.avatar_voice.src.tts.edge_tts_adapter import EdgeTTSAdapter
from modules.avatar_voice.src.tts.fallback_adapter import FallbackTTSAdapter
from modules.avatar_voice.src.tts.factory import ResilientTTSAdapter, TTSFactory

__all__ = [
    "TTSAdapter",
    "VOICE_CATALOG",
    "resolve_voice_id",
    "EdgeTTSAdapter",
    "FallbackTTSAdapter",
    "ResilientTTSAdapter",
    "TTSFactory",
]
