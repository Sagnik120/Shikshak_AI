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
    """Renders programming snippets, step-by-step algorithms, and execution flows inside an IDE window."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = visual_spec.get("content") if isinstance(visual_spec, dict) else getattr(visual_spec, "content", visual_spec)
        steps = visual_spec.get("steps") if isinstance(visual_spec, dict) else getattr(visual_spec, "steps", None)
        exec_out = visual_spec.get("execution_output") if isinstance(visual_spec, dict) else getattr(visual_spec, "execution_output", None)

        session_id = uuid.uuid4().hex[:8]
        code_str = ""
        lang = "python"
        output_str = str(exec_out or "").strip()

        if isinstance(content, dict):
            code_str = content.get("code", content.get("text", ""))
            lang = content.get("language", content.get("lang", "python"))
            if not output_str:
                output_str = content.get("output", "")
        else:
            code_str = str(content)

        if not code_str.strip():
            code_str = 'def calculate_fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)'

        # Check for multi-step progressive mode
        if steps and isinstance(steps, list) and len(steps) > 1:
            return self._render_progressive_code_steps(steps, lang, output_str, session_id)

        # If execution output is present, create progressive execution flow: Code -> Running -> Output
        if output_str:
            return self._render_progressive_execution_flow(code_str, lang, output_str, session_id)

        # Standard single code slide
        output_path = os.path.join(self.output_dir, f"code_{session_id}.png")
        self._render_code_canvas(code_str, lang, output_str="", active_line=-1, output_path=output_path)

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="code",
            step_image_paths=[output_path],
            is_progressive=False,
        )

    def _render_progressive_execution_flow(
        self,
        code_str: str,
        lang: str,
        output_str: str,
        session_id: str
    ) -> VisualRenderResult:
        """Render multi-stage execution flow: 1. Code Definition -> 2. Line Execution -> 3. Output Pane."""
        step_paths = []
        lines = code_str.strip().split("\n")[:14]
        last_exec_line = len(lines) - 1

        # Stage 1: Initial code definition (no terminal output)
        p1 = os.path.join(self.output_dir, f"code_{session_id}_step_1.png")
        self._render_code_canvas(code_str, lang, output_str="", active_line=-1, status_text="Definition", output_path=p1)
        step_paths.append(p1)

        # Stage 2: Code execution with active line highlighted
        p2 = os.path.join(self.output_dir, f"code_{session_id}_step_2.png")
        self._render_code_canvas(code_str, lang, output_str="", active_line=last_exec_line, status_text="Executing...", output_path=p2)
        step_paths.append(p2)

        # Stage 3: Terminal execution output revealed
        p3 = os.path.join(self.output_dir, f"code_{session_id}_step_3.png")
        self._render_code_canvas(code_str, lang, output_str=output_str, active_line=last_exec_line, status_text="Completed", output_path=p3)
        step_paths.append(p3)

        return VisualRenderResult(
            image_path=step_paths[-1],
            width=self.width,
            height=self.height,
            visual_type="code",
            step_image_paths=step_paths,
            is_progressive=True,
        )

    def _render_progressive_code_steps(
        self,
        steps: List[str],
        lang: str,
        output_str: str,
        session_id: str
    ) -> VisualRenderResult:
        """Render progressive code blocks revealed line by line."""
        step_paths = []
        for i, step_code in enumerate(steps):
            is_last = (i == len(steps) - 1)
            step_out = output_str if is_last else ""
            p = os.path.join(self.output_dir, f"code_{session_id}_step_{i + 1}.png")
            self._render_code_canvas(
                code_str=step_code,
                lang=lang,
                output_str=step_out,
                active_line=-1,
                status_text=f"Step {i + 1} of {len(steps)}",
                output_path=p
            )
            step_paths.append(p)

        return VisualRenderResult(
            image_path=step_paths[-1],
            width=self.width,
            height=self.height,
            visual_type="code",
            step_image_paths=step_paths,
            is_progressive=True,
        )

    def _render_code_canvas(
        self,
        code_str: str,
        lang: str,
        output_str: str,
        active_line: int,
        output_path: str,
        status_text: str = ""
    ) -> None:
        """Draw complete IDE window, syntax-highlighted lines, and output terminal."""
        subtitle = f"Source: {lang.upper()}"
        if status_text:
            subtitle += f" • Status: {status_text}"

        img, draw = self.create_canvas(title="Code Implementation & Execution Flow", subtitle=subtitle)

        ew_x1, ew_y1 = 80, 180
        ew_x2, ew_y2 = self.width - 80, self.height - (260 if output_str else 80)
        draw.rounded_rectangle([ew_x1, ew_y1, ew_x2, ew_y2], radius=12, fill=(10, 15, 30, 255), outline=THEME["card_border"], width=2)

        # Window header bar
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
            is_active = (idx == active_line)
            if is_active:
                draw.rectangle([ew_x1 + 66, code_y - 14, ew_x2 - 10, code_y + 18], fill=(35, 50, 80, 200))
                draw.rectangle([ew_x1 + 66, code_y - 14, ew_x1 + 70, code_y + 18], fill=THEME["accent_amber"])

            draw.text((ew_x1 + 45, code_y), str(idx + 1), fill=THEME["accent_amber"] if is_active else THEME["text_muted"], font=font_gutter, anchor="rm")
            
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
