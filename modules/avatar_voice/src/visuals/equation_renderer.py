"""
Equation Visual Renderer.
Renders LaTeX math formulas and equations to 1344x1080 canvas using Matplotlib mathtext
with font auto-scaling and broken-syntax fallback.
"""

import os
import uuid
from typing import Any, Dict, Union
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import BaseRenderer, THEME


class EquationRenderer(BaseRenderer):
    """Renders mathematical formulas, theorems, and equations."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = visual_spec.get("content") if isinstance(visual_spec, dict) else str(visual_spec)
        latex_str = str(content).strip() if content else "E = mc^2"
        session_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(self.output_dir, f"equation_{session_id}.png")

        rendered_successfully = False
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig = plt.figure(figsize=(13.44, 10.80), dpi=100)
            fig.patch.set_facecolor("#0f172a")

            ax = fig.add_axes([0.05, 0.12, 0.90, 0.75])
            ax.set_facecolor("#1e293b")
            for spine in ax.spines.values():
                spine.set_edgecolor("#334155")
                spine.set_linewidth(2)

            ax.set_xticks([])
            ax.set_yticks([])

            plt.suptitle(
                "Mathematical Formulation & Derivation",
                fontsize=24,
                fontweight="bold",
                color="#f8fafc",
                y=0.94,
                x=0.5,
            )

            formatted_latex = latex_str
            if not formatted_latex.startswith("$"):
                formatted_latex = f"${formatted_latex}$"

            fontsize = 36 if len(latex_str) < 30 else (26 if len(latex_str) < 70 else 20)

            ax.text(
                0.5,
                0.5,
                formatted_latex,
                fontsize=fontsize,
                color="#06b6d4",
                ha="center",
                va="center",
                transform=ax.transAxes,
                wrap=True,
            )

            fig.savefig(output_path, dpi=100, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            rendered_successfully = True
        except Exception:
            rendered_successfully = False

        if not rendered_successfully:
            img, draw = self.create_canvas(title="Mathematical Formula", subtitle="Equation Specification")
            font = self._get_font(32, bold=True)
            cx, cy = self.width // 2, (self.height + 140) // 2
            draw.rounded_rectangle([cx - 350, cy - 80, cx + 350, cy + 80], radius=12, fill=(15, 23, 42, 255), outline=THEME["accent_cyan"], width=3)
            draw.text((cx, cy), latex_str, fill=THEME["accent_cyan"], font=font, anchor="mm")
            font_note = self._get_font(16)
            draw.text((cx, cy + 110), "(Formal mathematical expression)", fill=THEME["text_muted"], font=font_note, anchor="mm")
            img.save(output_path, "PNG")

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="equation",
        )
