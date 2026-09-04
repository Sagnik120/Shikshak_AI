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
    """Renders mathematical formulas, theorems, and progressive derivations."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = visual_spec.get("content") if isinstance(visual_spec, dict) else getattr(visual_spec, "content", str(visual_spec))
        steps = visual_spec.get("steps") if isinstance(visual_spec, dict) else getattr(visual_spec, "steps", None)

        latex_str = str(content).strip() if content else "E = mc^2"
        session_id = uuid.uuid4().hex[:8]

        # Check for progressive steps
        step_list = []
        if steps and isinstance(steps, list) and len(steps) > 0:
            step_list = [str(s).strip() for s in steps if str(s).strip()]
        elif "\n" in latex_str and len([l for l in latex_str.split("\n") if l.strip()]) > 1:
            # Multi-line derivation provided in content
            step_list = [l.strip() for l in latex_str.split("\n") if l.strip()]

        if step_list and len(step_list) > 1:
            return self._render_progressive_steps(step_list, session_id)

        # Single static equation render
        output_path = os.path.join(self.output_dir, f"equation_{session_id}.png")
        self._render_single_latex(latex_str, output_path, title="Mathematical Formulation & Derivation")

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="equation",
            step_image_paths=[output_path],
            is_progressive=False,
        )

    def _render_progressive_steps(self, steps: List[str], session_id: str) -> VisualRenderResult:
        """Render a sequence of progressive derivation frames building upon each other."""
        step_paths = []
        total_steps = len(steps)

        for i in range(total_steps):
            step_path = os.path.join(self.output_dir, f"equation_{session_id}_step_{i + 1}.png")
            steps_so_far = steps[: i + 1]
            active_idx = i

            rendered = self._render_multi_step_frame(
                steps_so_far=steps_so_far,
                active_idx=active_idx,
                total_steps=total_steps,
                output_path=step_path
            )
            if not rendered:
                # Fallback to PIL canvas for this step
                self._render_multi_step_pil(
                    steps_so_far=steps_so_far,
                    active_idx=active_idx,
                    total_steps=total_steps,
                    output_path=step_path
                )
            step_paths.append(step_path)

        return VisualRenderResult(
            image_path=step_paths[-1],
            width=self.width,
            height=self.height,
            visual_type="equation",
            step_image_paths=step_paths,
            step_contents=steps,
            is_progressive=True,
        )

    def _render_multi_step_frame(
        self,
        steps_so_far: List[str],
        active_idx: int,
        total_steps: int,
        output_path: str
    ) -> bool:
        """Render multiple derivation steps using Matplotlib with active line highlighting."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig = plt.figure(figsize=(13.44, 10.80), dpi=100)
            fig.patch.set_facecolor("#0f172a")

            ax = fig.add_axes([0.05, 0.10, 0.90, 0.78])
            ax.set_facecolor("#1e293b")
            for spine in ax.spines.values():
                spine.set_edgecolor("#334155")
                spine.set_linewidth(2)

            ax.set_xticks([])
            ax.set_yticks([])

            plt.suptitle(
                f"Step-by-Step Derivation (Step {active_idx + 1} of {total_steps})",
                fontsize=24,
                fontweight="bold",
                color="#f8fafc",
                y=0.95,
                x=0.5,
            )

            # Calculate vertical positions evenly
            n = len(steps_so_far)
            y_start = 0.82
            y_spacing = min(0.70 / max(n, 1), 0.18)

            for idx, step_text in enumerate(steps_so_far):
                y_pos = y_start - (idx * y_spacing)
                is_active = (idx == active_idx)

                formatted = step_text
                if not formatted.startswith("$"):
                    formatted = f"${formatted}$"

                color = "#06b6d4" if is_active else "#94a3b8"
                fontsize = 28 if is_active else 22

                # Prefix label
                step_label = f"Step {idx + 1}: "
                ax.text(
                    0.08,
                    y_pos,
                    step_label,
                    fontsize=20,
                    fontweight="bold" if is_active else "normal",
                    color="#f59e0b" if is_active else "#64748b",
                    ha="left",
                    va="center",
                    transform=ax.transAxes,
                )

                ax.text(
                    0.25,
                    y_pos,
                    formatted,
                    fontsize=fontsize,
                    color=color,
                    ha="left",
                    va="center",
                    transform=ax.transAxes,
                )

            fig.savefig(output_path, dpi=100, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            return True
        except Exception:
            return False

    def _render_multi_step_pil(
        self,
        steps_so_far: List[str],
        active_idx: int,
        total_steps: int,
        output_path: str
    ) -> None:
        """Pillow fallback for multi-step progressive derivation."""
        img, draw = self.create_canvas(
            title=f"Step-by-Step Mathematical Derivation",
            subtitle=f"Stage {active_idx + 1} of {total_steps}"
        )
        font_active = self._get_font(26, bold=True)
        font_past = self._get_font(22)
        font_tag = self._get_font(18, bold=True)

        y_pos = 180
        for idx, step_text in enumerate(steps_so_far):
            is_active = (idx == active_idx)
            card_fill = (20, 35, 55, 255) if is_active else (25, 30, 45, 255)
            border_color = THEME["accent_cyan"] if is_active else THEME["card_border"]

            draw.rounded_rectangle([80, y_pos, self.width - 80, y_pos + 70], radius=8, fill=card_fill, outline=border_color, width=2 if is_active else 1)
            draw.text((110, y_pos + 35), f"Step {idx + 1}", fill=THEME["accent_amber"] if is_active else THEME["text_muted"], font=font_tag, anchor="lm")
            draw.text((220, y_pos + 35), step_text, fill=THEME["accent_cyan"] if is_active else THEME["text_muted"], font=font_active if is_active else font_past, anchor="lm")
            y_pos += 90

        img.save(output_path, "PNG")

    def _render_single_latex(self, latex_str: str, output_path: str, title: str) -> None:
        """Render a single LaTeX equation."""
        rendered = False
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
                title,
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
            rendered = True
        except Exception:
            rendered = False

        if not rendered:
            img, draw = self.create_canvas(title="Mathematical Formula", subtitle="Equation Specification")
            font = self._get_font(32, bold=True)
            cx, cy = self.width // 2, (self.height + 140) // 2
            draw.rounded_rectangle([cx - 350, cy - 80, cx + 350, cy + 80], radius=12, fill=(15, 23, 42, 255), outline=THEME["accent_cyan"], width=3)
            draw.text((cx, cy), latex_str, fill=THEME["accent_cyan"], font=font, anchor="mm")
            font_note = self._get_font(16)
            draw.text((cx, cy + 110), "(Formal mathematical expression)", fill=THEME["text_muted"], font=font_note, anchor="mm")
            img.save(output_path, "PNG")
