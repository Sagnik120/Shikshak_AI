"""
Timeline Visual Renderer.
Renders sequential progression steps, chronological milestones, and stage trackers.
"""

import json
import os
import uuid
from typing import Any, Dict, List, Union
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import BaseRenderer, THEME


class TimelineRenderer(BaseRenderer):
    """Renders horizontal milestone sequences and chronological progressions."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = visual_spec.get("content") if isinstance(visual_spec, dict) else visual_spec
        session_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(self.output_dir, f"timeline_{session_id}.png")

        events: List[Dict[str, str]] = []
        title = "Chronological Timeline & Milestone Track"

        if isinstance(content, dict):
            title = content.get("title", title)
            events = content.get("events", content.get("milestones", []))
        elif isinstance(content, list):
            events = [e if isinstance(e, dict) else {"label": str(e), "step": f"Phase {i+1}"} for i, e in enumerate(content)]
        elif isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    events = [e if isinstance(e, dict) else {"label": str(e), "step": f"Step {i+1}"} for i, e in enumerate(parsed)]
            except Exception:
                events = [{"step": f"Stage {i+1}", "label": l.strip()} for i, l in enumerate(content.split("\n")) if l.strip()]

        if not events:
            events = [
                {"step": "Step 1", "label": "Problem Formulation"},
                {"step": "Step 2", "label": "Feature Extraction"},
                {"step": "Step 3", "label": "Model Optimization"},
                {"step": "Step 4", "label": "Evaluation & Deployment"},
            ]

        img, draw = self.create_canvas(title=title, subtitle="Sequential Milestone Roadmap")

        num_events = len(events[:5])
        axis_y = 520
        start_x = 140
        spacing = min(240, int((self.width - 280) / max(1, num_events - 1)))

        end_x = start_x + (num_events - 1) * spacing
        draw.line([(start_x, axis_y), (end_x, axis_y)], fill=THEME["card_border"], width=8)
        draw.line([(start_x, axis_y), (end_x, axis_y)], fill=THEME["accent_cyan"], width=4)

        font_step = self._get_font(16, bold=True)
        font_label = self._get_font(18)

        colors = [THEME["accent_cyan"], THEME["accent_teal"], THEME["accent_amber"], THEME["accent_indigo"], THEME["accent_rose"]]

        for idx, event in enumerate(events[:5]):
            cx = start_x + idx * spacing
            accent = colors[idx % len(colors)]

            draw.ellipse([cx - 24, axis_y - 24, cx + 24, axis_y + 24], fill=THEME["card_bg"], outline=accent, width=4)
            draw.ellipse([cx - 10, axis_y - 10, cx + 10, axis_y + 10], fill=accent)

            step_title = event.get("step", f"Phase {idx+1}")
            label = event.get("label", event.get("title", ""))

            card_w = 200
            card_h = 110
            card_x = cx - card_w // 2

            if idx % 2 == 0:
                card_y = axis_y - 180
                draw.line([(cx, card_y + card_h), (cx, axis_y - 26)], fill=accent, width=2)
            else:
                card_y = axis_y + 70
                draw.line([(cx, axis_y + 26), (cx, card_y)], fill=accent, width=2)

            draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=10, fill=THEME["card_bg"], outline=accent, width=2)
            draw.text((cx, card_y + 28), step_title, fill=accent, font=font_step, anchor="mm")
            draw.text((cx, card_y + 65), label, fill=THEME["text_main"], font=font_label, anchor="mm")

        img.save(output_path, "PNG")

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="timeline",
        )
