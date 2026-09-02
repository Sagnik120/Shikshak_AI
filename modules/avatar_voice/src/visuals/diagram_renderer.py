"""
Diagram Visual Renderer.
Renders structured process flowcharts, concept hierarchies, and network nodes with arrows.
"""

import json
import os
import uuid
from typing import Any, Dict, List, Union
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import BaseRenderer, THEME


class DiagramRenderer(BaseRenderer):
    """Renders structured diagrams, flowcharts, and concept relationship maps."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = visual_spec.get("content") if isinstance(visual_spec, dict) else visual_spec
        session_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(self.output_dir, f"diagram_{session_id}.png")

        nodes: List[str] = []
        title = "Concept Architecture & Process Flow"

        if isinstance(content, dict):
            title = content.get("title", title)
            if "nodes" in content:
                nodes = [n.get("label", str(n)) if isinstance(n, dict) else str(n) for n in content["nodes"]]
            elif "steps" in content:
                nodes = [str(s) for s in content["steps"]]
        elif isinstance(content, list):
            nodes = [str(x) for x in content]
        elif isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    title = parsed.get("title", title)
                    nodes = [str(x) for x in parsed.get("nodes", parsed.get("steps", []))]
                elif isinstance(parsed, list):
                    nodes = [str(x) for x in parsed]
            except Exception:
                nodes = [line.strip() for line in content.split("\n") if line.strip()]
                if not nodes:
                    nodes = [content]

        if not nodes:
            nodes = ["Input Data", "Processing Engine", "Adaptive Reasoning", "Optimized Output"]

        img, draw = self.create_canvas(title=title, subtitle="System Diagram & Flow Model")

        num_nodes = len(nodes[:5])
        card_w = min(220, int((1100 - (num_nodes - 1) * 60) / max(1, num_nodes)))
        card_h = 160
        start_x = 100
        start_y = 480

        font_node = self._get_font(18, bold=True)
        font_num = self._get_font(14)

        colors = [THEME["accent_cyan"], THEME["accent_teal"], THEME["accent_indigo"], THEME["accent_amber"], THEME["accent_rose"]]

        for idx, label in enumerate(nodes[:5]):
            bx = start_x + idx * (card_w + 60)
            by = start_y
            accent = colors[idx % len(colors)]

            draw.rounded_rectangle([bx, by, bx + card_w, by + card_h], radius=12, fill=THEME["card_bg"], outline=accent, width=3)
            draw.rounded_rectangle([bx + 12, by + 12, bx + 50, by + 36], radius=6, fill=accent)
            draw.text((bx + 31, by + 24), f"#{idx+1}", fill=(15, 23, 42, 255), font=font_num, anchor="mm")

            words = label.split()
            lines = []
            cur_line = []
            for w in words:
                cur_line.append(w)
                if len(" ".join(cur_line)) > 14:
                    lines.append(" ".join(cur_line))
                    cur_line = []
            if cur_line:
                lines.append(" ".join(cur_line))

            text_y = by + 60
            for l in lines[:3]:
                draw.text((bx + card_w // 2, text_y), l, fill=THEME["text_main"], font=font_node, anchor="mm")
                text_y += 24

            if idx < num_nodes - 1:
                ax_start = bx + card_w + 8
                ax_end = ax_start + 44
                ay = by + card_h // 2
                draw.line([(ax_start, ay), (ax_end, ay)], fill=THEME["accent_cyan"], width=4)
                draw.polygon([(ax_end, ay - 6), (ax_end + 10, ay), (ax_end, ay + 6)], fill=THEME["accent_cyan"])

        img.save(output_path, "PNG")

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="diagram",
        )
