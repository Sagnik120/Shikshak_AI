"""
Map Visual Renderer.
Renders schematic coordinate maps and spatial region markers without external map API dependencies.
"""

import json
import os
import uuid
from typing import Any, Dict, List, Union
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import BaseRenderer, THEME


class MapRenderer(BaseRenderer):
    """Renders geographical schematics, spatial regions, and coordinate point maps."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = visual_spec.get("content") if isinstance(visual_spec, dict) else visual_spec
        session_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(self.output_dir, f"map_{session_id}.png")

        title = "Geographic & Spatial Distribution"
        markers: List[Dict[str, Any]] = []

        if isinstance(content, dict):
            title = content.get("title", title)
            markers = content.get("markers", content.get("points", []))
        elif isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    title = parsed.get("title", title)
                    markers = parsed.get("markers", [])
            except Exception:
                markers = [{"label": content, "x": 0.5, "y": 0.5}]

        if not markers:
            markers = [
                {"label": "Region A (North Hub)", "x": 0.35, "y": 0.35},
                {"label": "Region B (Central Zone)", "x": 0.55, "y": 0.52},
                {"label": "Region C (Coastal Port)", "x": 0.72, "y": 0.68},
            ]

        img, draw = self.create_canvas(title=title, subtitle="Schematic Coordinate Model")

        map_x1, map_y1 = 100, 180
        map_x2, map_y2 = self.width - 100, self.height - 80
        draw.rounded_rectangle([map_x1, map_y1, map_x2, map_y2], radius=14, fill=(10, 20, 35, 255), outline=THEME["card_border"], width=2)

        for gx in range(map_x1 + 100, map_x2, 120):
            draw.line([(gx, map_y1), (gx, map_y2)], fill=(25, 40, 65, 255), width=1)
        for gy in range(map_y1 + 100, map_y2, 100):
            draw.line([(map_x1, gy), (map_x2, gy)], fill=(25, 40, 65, 255), width=1)

        font_marker = self._get_font(16, bold=True)

        for m in markers:
            label = m.get("label", "Location")
            nx = float(m.get("x", 0.5))
            ny = float(m.get("y", 0.5))

            px = int(map_x1 + nx * (map_x2 - map_x1))
            py = int(map_y1 + ny * (map_y2 - map_y1))

            draw.ellipse([px - 28, py - 28, px + 28, py + 28], outline=(6, 182, 212, 100), width=2)
            draw.ellipse([px - 14, py - 14, px + 14, py + 14], fill=THEME["accent_cyan"], outline=(255, 255, 255, 255), width=2)

            badge_w = len(label) * 11 + 24
            bx = min(map_x2 - badge_w - 10, max(map_x1 + 10, px - badge_w // 2))
            by = py - 52
            draw.rounded_rectangle([bx, by, bx + badge_w, by + 32], radius=6, fill=THEME["card_bg"], outline=THEME["accent_cyan"], width=2)
            draw.text((bx + badge_w // 2, by + 16), label, fill=THEME["text_main"], font=font_marker, anchor="mm")

        img.save(output_path, "PNG")

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="map",
        )
