"""
Base interfaces and protocols for visual synthesis renderers.
Canvas target: 1344x1080 (70% viewport of 1920x1080 video canvas).
"""

import os
import tempfile
from typing import Any, Dict, Protocol, Tuple, Union
from PIL import Image, ImageDraw, ImageFont
from modules.avatar_voice.src.models import VisualRenderResult

THEME = {
    "bg": (15, 23, 42, 255),
    "card_bg": (30, 41, 59, 255),
    "card_border": (51, 65, 85, 255),
    "text_main": (248, 250, 252, 255),
    "text_muted": (148, 163, 184, 255),
    "accent_cyan": (6, 182, 212, 255),
    "accent_teal": (20, 184, 166, 255),
    "accent_amber": (245, 158, 11, 255),
    "accent_indigo": (99, 102, 241, 255),
    "accent_rose": (244, 63, 94, 255),
}


class VisualRenderer(Protocol):
    """Protocol for specialized subject-aware visual renderers."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        """Render the given visual spec into an image asset."""
        ...


class BaseRenderer:
    """Helper base class providing standard 1344x1080 canvas creation and layout tools."""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(tempfile.gettempdir(), "shikshak_visuals")
        os.makedirs(self.output_dir, exist_ok=True)
        self.width = 1344
        self.height = 1080

    def create_canvas(self, title: str = "", subtitle: str = "") -> Tuple[Image.Image, ImageDraw.Draw]:
        """Create a stylized 1344x1080 slide canvas with header banner."""
        img = Image.new("RGBA", (self.width, self.height), THEME["bg"])
        draw = ImageDraw.Draw(img)

        draw.rectangle([40, 30, self.width - 40, 120], fill=THEME["card_bg"], outline=THEME["card_border"], width=2)
        draw.rounded_rectangle([45, 35, 55, 115], radius=4, fill=THEME["accent_cyan"])

        font_title = self._get_font(28, bold=True)
        draw.text((70, 48), title or "Concept Explanation", fill=THEME["text_main"], font=font_title)

        if subtitle:
            font_sub = self._get_font(18)
            draw.text((70, 84), subtitle, fill=THEME["text_muted"], font=font_sub)

        draw.rectangle([40, 140, self.width - 40, self.height - 40], fill=THEME["card_bg"], outline=THEME["card_border"], width=2)

        return img, draw

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Retrieve appropriate font with cross-platform fallback."""
        try:
            font_names = [
                "Helvetica", "Arial", "DejaVuSans", "NotoSans-Regular",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ]
            for fn in font_names:
                try:
                    return ImageFont.truetype(fn, size)
                except Exception:
                    continue
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()
