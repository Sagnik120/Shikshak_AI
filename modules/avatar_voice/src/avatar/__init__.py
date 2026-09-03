"""
Avatar Subsystem package exports.
"""

from modules.avatar_voice.src.avatar.base import AvatarAdapter
from modules.avatar_voice.src.avatar.viseme_avatar import VisemeAvatarAdapter
from modules.avatar_voice.src.avatar.wav2lip_avatar import Wav2LipAvatarAdapter
from modules.avatar_voice.src.avatar.musetalk_avatar import MuseTalkAvatarAdapter
from modules.avatar_voice.src.avatar.factory import AvatarFactory

__all__ = [
    "AvatarAdapter",
    "VisemeAvatarAdapter",
    "Wav2LipAvatarAdapter",
    "MuseTalkAvatarAdapter",
    "AvatarFactory",
]
