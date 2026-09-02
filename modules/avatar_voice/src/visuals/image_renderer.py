"""
Image Visual Renderer.
Renders concept cards, illustrative graphics, and curated diagram assets.
"""

import os
import uuid
from typing import Any, Dict, Union
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import BaseRenderer, THEME


class ImageRenderer(BaseRenderer):
    """Renders visual cards, concept imagery, and graphic illustrations."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = visual_spec.get("content") if isinstance(visual_spec, dict) else visual_spec
        session_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(self.output_dir, f"image_{session_id}.png")

        prompt_or_caption = str(content) if content else "Concept Visualization"
        title = "Concept Visualization & Overview"

        img, draw = self.create_canvas(title=title, subtitle="Multimodal Visual Aid")

        card_x1, card_y1 = 120, 200
        card_x2, card_y2 = self.width - 120, self.height - 100
        draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=16, fill=(18, 26, 45, 255), outline=THEME["card_border"], width=3)

        cx = (card_x1 + card_x2) // 2
        cy = (card_y1 + card_y2) // 2 - 30

        draw.ellipse([cx - 140, cy - 140, cx + 140, cy + 140], outline=THEME["accent_indigo"], width=3)
        draw.ellipse([cx - 100, cy - 100, cx + 100, cy + 100], fill=(30, 41, 59, 255), outline=THEME["accent_cyan"], width=4)
        draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=THEME["accent_teal"])

        font_caption = self._get_font(22, bold=True)
        draw.text((cx, cy + 170), prompt_or_caption[:65], fill=THEME["text_main"], font=font_caption, anchor="mm")

        img.save(output_path, "PNG")

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="image",
        )
