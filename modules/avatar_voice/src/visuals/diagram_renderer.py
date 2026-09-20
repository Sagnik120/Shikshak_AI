"""
Diagram Visual Renderer.
Renders structured process flowcharts, concept hierarchies, and network nodes with arrows.
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Union
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import BaseRenderer, THEME

logger = logging.getLogger(__name__)


class DiagramRenderer(BaseRenderer):
    """Renders structured diagrams, flowcharts, and concept relationship maps."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = (
            visual_spec.get("content")
            if isinstance(visual_spec, dict)
            # A VisualSpec model arrives here, not a dict: without the
            # attribute lookup the whole object became "content", no
            # branch below matched it, and every board fell through to
            # placeholder labels.
            else getattr(visual_spec, "content", visual_spec)
        )
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

        # Sample labels ("Input Data → Processing Engine") used to render whenever
        # the spec was empty or off-schema, putting unrelated content on a physics
        # board. A takeaway card built from the real title is always topical.
        nodes = [n for n in nodes if str(n).strip()]
        if not nodes:
            logger.warning(
                "Diagram spec had no usable nodes; falling back to a concept takeaway card for %r",
                title,
            )
            return self._render_takeaway_fallback(title, content, output_path)

        img, draw = self.create_canvas(title=title, subtitle="")

        num_nodes = len(nodes[:5])
        card_w = min(340, int((1180 - (num_nodes - 1) * 50) / max(1, num_nodes)))
        # Fill the board area (roughly y=150..1040) instead of leaving two thirds
        # of it empty, which is what made the old boards look sparse on video.
        card_h = 440
        board_top, board_bottom = 170, self.height - 60
        start_x = (self.width - (num_nodes * card_w + (num_nodes - 1) * 50)) // 2
        start_y = board_top + ((board_bottom - board_top) - card_h) // 2

        font_node = self._get_font(30, bold=True)
        font_num = self._get_font(20, bold=True)

        colors = [THEME["accent_cyan"], THEME["accent_teal"], THEME["accent_indigo"], THEME["accent_amber"], THEME["accent_rose"]]

        for idx, label in enumerate(nodes[:5]):
            bx = start_x + idx * (card_w + 50)
            by = start_y
            accent = colors[idx % len(colors)]

            draw.rounded_rectangle([bx, by, bx + card_w, by + card_h], radius=16, fill=THEME["card_bg"], outline=accent, width=4)
            draw.rounded_rectangle([bx + 16, by + 16, bx + 74, by + 52], radius=8, fill=accent)
            draw.text((bx + 45, by + 34), f"#{idx+1}", fill=(15, 23, 42, 255), font=font_num, anchor="mm")

            lines = self._wrap_label(str(label), max_chars=max(10, card_w // 17))

            line_h = 40
            text_y = by + (card_h + 60) // 2 - (len(lines[:4]) - 1) * line_h // 2
            for l in lines[:4]:
                draw.text((bx + card_w // 2, text_y), l, fill=THEME["text_main"], font=font_node, anchor="mm")
                text_y += line_h

            if idx < num_nodes - 1:
                ax_start = bx + card_w + 8
                ax_end = ax_start + 34
                ay = by + card_h // 2
                draw.line([(ax_start, ay), (ax_end, ay)], fill=THEME["accent_cyan"], width=5)
                draw.polygon([(ax_end, ay - 9), (ax_end + 14, ay), (ax_end, ay + 9)], fill=THEME["accent_cyan"])

        img.save(output_path, "PNG")

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="diagram",
        )

    # -- helpers -------------------------------------------------------------

    def _wrap_label(self, label: str, max_chars: int) -> List[str]:
        """Word-wrap a node label so long stage names stay inside their card."""
        lines: List[str] = []
        current = ""
        for word in label.split():
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > max_chars:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines or [label]

    def _render_takeaway_fallback(self, title: str, content: Any, output_path: str) -> VisualRenderResult:
        """Title + concept takeaway card, used when the spec has no usable nodes."""
        img, draw = self.create_canvas(title=title, subtitle="")

        body = content if isinstance(content, str) else ""
        if isinstance(content, dict):
            body = str(content.get("summary") or content.get("description") or "")

        bullets: List[str] = []
        for sentence in str(body).replace("\n", " ").split(". "):
            sentence = sentence.strip(" .")
            if sentence:
                bullets.append(sentence)
        bullets = bullets[:4]

        font_bullet = self._get_font(36)
        y = 300
        for bullet in bullets:
            for i, line in enumerate(self._wrap_label(bullet, max_chars=58)[:2]):
                if i == 0:
                    draw.ellipse([110, y + 14, 128, y + 32], fill=THEME["accent_cyan"])
                draw.text((160, y), line, fill=THEME["text_main"], font=font_bullet)
                y += 50
            y += 24

        if not bullets:
            font_note = self._get_font(40)
            draw.text(
                (self.width // 2, (self.height + 140) // 2),
                title,
                fill=THEME["text_main"], font=font_note, anchor="mm",
            )

        img.save(output_path, "PNG")
        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="diagram",
        )
