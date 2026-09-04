"""
Base interfaces and protocols for Text-to-Speech synthesis.
Strictly conforms to Contract.md §14 (TTSAdapter).
"""

from typing import Dict, List, Protocol
from modules.avatar_voice.src.models import TTSResult, WordTimestamp

VOICE_CATALOG: Dict[str, Dict[str, str]] = {
    "bn": {
        "female": "bn-IN-TanishaaNeural",
        "male": "bn-IN-BashkarNeural",
        "default": "bn-IN-TanishaaNeural",
    },
    "bengali": {
        "female": "bn-IN-TanishaaNeural",
        "male": "bn-IN-BashkarNeural",
        "default": "bn-IN-TanishaaNeural",
    },
    "hi": {
        "female": "hi-IN-SwaraNeural",
        "male": "hi-IN-MadhurNeural",
        "default": "hi-IN-SwaraNeural",
    },
    "hindi": {
        "female": "hi-IN-SwaraNeural",
        "male": "hi-IN-MadhurNeural",
        "default": "hi-IN-SwaraNeural",
    },
    "en-in": {
        "female": "en-IN-NeerjaNeural",
        "male": "en-IN-PrabhatNeural",
        "default": "en-IN-NeerjaNeural",
    },
    "hinglish": {
        "female": "hi-IN-SwaraNeural",
        "male": "hi-IN-MadhurNeural",
        "default": "hi-IN-SwaraNeural",
    },
    "en": {
        "female": "en-US-AriaNeural",
        "male": "en-US-GuyNeural",
        "default": "en-US-AriaNeural",
    },
    "english": {
        "female": "en-US-AriaNeural",
        "male": "en-US-GuyNeural",
        "default": "en-US-AriaNeural",
    },
}


def resolve_voice_id(language: str, gender: str = "female") -> str:
    """Resolve the appropriate neural voice ID for a given language code."""
    lang_key = language.strip().lower()
    if lang_key in VOICE_CATALOG:
        return VOICE_CATALOG[lang_key].get(gender.lower(), VOICE_CATALOG[lang_key]["default"])
    if "bn" in lang_key or "bengali" in lang_key or "bangla" in lang_key:
        return VOICE_CATALOG["bn"]["default"]
    if "hi" in lang_key:
        return VOICE_CATALOG["hi"]["default"]
    if "in" in lang_key:
        return VOICE_CATALOG["en-in"]["default"]
    return VOICE_CATALOG["en"]["default"]


class TTSAdapter(Protocol):
    """Protocol for Text-to-Speech synthesis per Contract §14."""

    def synthesize(
        self,
        text: str,
        language: str = "en",
        voice_id: Optional[str] = None,
        avatar_cue: str = "neutral"
    ) -> TTSResult:
        """Synthesize spoken narration audio and timing metadata from text."""
        ...
