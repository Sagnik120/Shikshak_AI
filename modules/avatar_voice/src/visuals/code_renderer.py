"""
Code Visual Renderer.
Renders syntax-highlighted code editor windows with line numbers, language pills,
and optional execution console output panels.
"""

import os
import uuid
from typing import Any, Dict, List, Union
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import BaseRenderer, THEME


class CodeRenderer(BaseRenderer):
    """Renders programming snippets and algorithms inside an IDE-style window."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = visual_spec.get("content") if isinstance(visual_spec, dict) else visual_spec
        session_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(self.output_dir, f"code_{session_id}.png")

        code_str = ""
        lang = "python"
        output_str = ""

        if isinstance(content, dict):
            code_str = content.get("code", content.get("text", ""))
            lang = content.get("language", content.get("lang", "python"))
            output_str = content.get("output", "")
        else:
            code_str = str(content)

        if not code_str.strip():
            code_str = 'def calculate_fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)'

        img, draw = self.create_canvas(title="Code Implementation & Algorithm", subtitle=f"Source Language: {lang.upper()}")

        ew_x1, ew_y1 = 80, 180
        ew_x2, ew_y2 = self.width - 80, self.height - (260 if output_str else 80)
        draw.rounded_rectangle([ew_x1, ew_y1, ew_x2, ew_y2], radius=12, fill=(10, 15, 30, 255), outline=THEME["card_border"], width=2)

        draw.rounded_rectangle([ew_x1, ew_y1, ew_x2, ew_y1 + 45], radius=12, fill=(20, 28, 48, 255))
        draw.ellipse([ew_x1 + 18, ew_y1 + 16, ew_x1 + 30, ew_y1 + 28], fill=(239, 68, 68, 255))
        draw.ellipse([ew_x1 + 38, ew_y1 + 16, ew_x1 + 50, ew_y1 + 28], fill=(245, 158, 11, 255))
        draw.ellipse([ew_x1 + 58, ew_y1 + 16, ew_x1 + 70, ew_y1 + 28], fill=(34, 197, 94, 255))

        font_tab = self._get_font(14, bold=True)
        draw.rounded_rectangle([ew_x1 + 90, ew_y1 + 10, ew_x1 + 230, ew_y1 + 38], radius=6, fill=(30, 41, 59, 255))
        draw.text((ew_x1 + 160, ew_y1 + 24), f"solution.{lang}", fill=THEME["text_main"], font=font_tab, anchor="mm")

        lines = code_str.strip().split("\n")[:14]
        font_code = self._get_font(20)
        font_gutter = self._get_font(18)

        draw.line([(ew_x1 + 65, ew_y1 + 45), (ew_x1 + 65, ew_y2)], fill=THEME["card_border"], width=1)

        code_y = ew_y1 + 65
        for idx, line in enumerate(lines):
            draw.text((ew_x1 + 45, code_y), str(idx + 1), fill=THEME["text_muted"], font=font_gutter, anchor="rm")
            
            line_x = ew_x1 + 85
            words = line.split(" ")
            for w in words:
                color = THEME["text_main"]
                if w in ["def", "class", "return", "import", "from", "if", "else", "elif", "for", "while", "in"]:
                    color = THEME["accent_rose"]
                elif w in ["int", "str", "float", "bool", "list", "dict", "True", "False"]:
                    color = THEME["accent_cyan"]
                elif w.startswith('"') or w.startswith("'") or w.endswith('"') or w.endswith("'"):
                    color = THEME["accent_teal"]
                elif w.startswith("#"):
                    color = THEME["text_muted"]

                draw.text((line_x, code_y), w + " ", fill=color, font=font_code, anchor="lm")
                line_x += len(w + " ") * 12

            code_y += 32

        if output_str:
            ow_y1 = ew_y2 + 20
            ow_y2 = self.height - 60
            draw.rounded_rectangle([ew_x1, ow_y1, ew_x2, ow_y2], radius=8, fill=(5, 10, 20, 255), outline=THEME["accent_teal"], width=2)
            font_term_title = self._get_font(14, bold=True)
            draw.text((ew_x1 + 20, ow_y1 + 18), "OUTPUT TERMINAL >", fill=THEME["accent_teal"], font=font_term_title, anchor="lm")
            font_term_out = self._get_font(18)
            draw.text((ew_x1 + 20, ow_y1 + 50), str(output_str), fill=THEME["text_main"], font=font_term_out, anchor="lm")

        img.save(output_path, "PNG")

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="code",
        )
