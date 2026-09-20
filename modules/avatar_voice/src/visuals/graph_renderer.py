"""
Graph Visual Renderer.
Renders statistical plots, coordinate functions, and bar/line charts using Matplotlib.
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, Union
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import BaseRenderer, THEME

logger = logging.getLogger(__name__)


class GraphRenderer(BaseRenderer):
    """Renders 2D coordinate graphs, line plots, and distributions."""

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
        output_path = os.path.join(self.output_dir, f"graph_{session_id}.png")

        spec_dict = {}
        if isinstance(content, dict):
            spec_dict = content
        elif isinstance(content, str):
            try:
                spec_dict = json.loads(content)
            except Exception:
                spec_dict = {"title": content, "type": "line"}

        chart_type = spec_dict.get("type", "line").lower()
        title = spec_dict.get("title", "Function & Data Analysis")
        xlabel = spec_dict.get("xlabel", "Input X")
        ylabel = spec_dict.get("ylabel", "Output Y")

        x_data, y_data = self._extract_series(spec_dict)
        if not y_data:
            # Defaulting to a built-in 2,4,8..256 curve drew a fabricated
            # exponential and presented it to the learner as this concept's
            # real data. A title card states nothing that isn't true.
            logger.warning(
                "Graph spec had no usable series; falling back to a title card for %r", title
            )
            return self._render_title_card(title, output_path)

        rendered = False
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(13.44, 10.80), dpi=100)
            fig.patch.set_facecolor("#0f172a")
            ax.set_facecolor("#1e293b")

            for spine in ax.spines.values():
                spine.set_edgecolor("#334155")
                spine.set_linewidth(2)

            ax.grid(True, linestyle="--", alpha=0.3, color="#64748b")
            ax.tick_params(colors="#94a3b8", labelsize=14)

            if chart_type == "bar":
                bars = ax.bar(range(len(y_data)), y_data, color="#06b6d4", edgecolor="#14b8a6", width=0.6)
                if isinstance(x_data[0], str):
                    ax.set_xticks(range(len(x_data)))
                    ax.set_xticklabels(x_data, rotation=15)
            elif chart_type == "scatter":
                ax.scatter(x_data, y_data, color="#f43f5e", s=180, edgecolors="#ffffff", linewidths=2)
            else:
                ax.plot(x_data, y_data, color="#06b6d4", linewidth=4, marker="o", markersize=10, markerfacecolor="#ffffff")

            ax.set_title(title, fontsize=24, fontweight="bold", color="#f8fafc", pad=20)
            ax.set_xlabel(xlabel, fontsize=18, color="#cbd5e1", labelpad=14)
            ax.set_ylabel(ylabel, fontsize=18, color="#cbd5e1", labelpad=14)

            plt.tight_layout(rect=[0.05, 0.08, 0.95, 0.95])
            fig.savefig(output_path, dpi=100, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            rendered = True
        except Exception:
            rendered = False

        if not rendered:
            img, draw = self.create_canvas(title=title, subtitle="Graphical Representation")
            ox, oy = 180, 850
            draw.line([(ox, 240), (ox, oy)], fill=THEME["text_muted"], width=3)
            draw.line([(ox, oy), (1180, oy)], fill=THEME["text_muted"], width=3)
            num_bars = len(y_data)
            bar_w = 60
            for i, val in enumerate(y_data[:8]):
                bx = ox + 60 + i * (bar_w + 50)
                norm_h = min(500, int((float(val) / (max(y_data) or 1)) * 480))
                by = oy - norm_h
                draw.rounded_rectangle([bx, by, bx + bar_w, oy], radius=6, fill=THEME["accent_cyan"])
            img.save(output_path, "PNG")

        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="graph",
        )

    # -- helpers -------------------------------------------------------------

    def _extract_series(self, spec: Dict[str, Any]) -> tuple:
        """Pull an (x, y) series out of the shapes models actually emit.

        Beyond plain x/y, a model commonly returns points/data/series as pairs
        or as a list of numbers. Anything unrecognised returns empty so the
        caller can fall back rather than invent data.
        """
        x_data = spec.get("x") or spec.get("x_values") or spec.get("labels")
        y_data = spec.get("y") or spec.get("y_values") or spec.get("values")

        if not y_data:
            pairs = spec.get("points") or spec.get("data") or spec.get("series")
            if isinstance(pairs, list) and pairs:
                if all(isinstance(pt, (list, tuple)) and len(pt) >= 2 for pt in pairs):
                    x_data = [pt[0] for pt in pairs]
                    y_data = [pt[1] for pt in pairs]
                elif all(isinstance(pt, dict) for pt in pairs):
                    x_data = [pt.get("x", i) for i, pt in enumerate(pairs)]
                    y_data = [pt.get("y") for pt in pairs]
                elif all(isinstance(pt, (int, float)) for pt in pairs):
                    y_data = list(pairs)
                    x_data = list(range(1, len(pairs) + 1))

        if not isinstance(y_data, list) or not y_data:
            return [], []
        if any(v is None for v in y_data):
            return [], []
        if not isinstance(x_data, list) or len(x_data) != len(y_data):
            x_data = list(range(1, len(y_data) + 1))
        return x_data, y_data

    def _render_title_card(self, title: str, output_path: str) -> VisualRenderResult:
        """Board stating only the concept, for a spec with no plottable data."""
        img, draw = self.create_canvas(title=title, subtitle="")
        font = self._get_font(44, bold=True)
        draw.text(
            (self.width // 2, (self.height + 140) // 2),
            title,
            fill=THEME["text_main"], font=font, anchor="mm",
        )
        img.save(output_path, "PNG")
        return VisualRenderResult(
            image_path=output_path,
            width=self.width,
            height=self.height,
            visual_type="graph",
        )
