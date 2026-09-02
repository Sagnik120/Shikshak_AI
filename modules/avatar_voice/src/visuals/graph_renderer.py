"""
Graph Visual Renderer.
Renders statistical plots, coordinate functions, and bar/line charts using Matplotlib.
"""

import json
import os
import uuid
from typing import Any, Dict, Union
from PIL import Image, ImageDraw
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import BaseRenderer, THEME


class GraphRenderer(BaseRenderer):
    """Renders 2D coordinate graphs, line plots, and distributions."""

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        content = visual_spec.get("content") if isinstance(visual_spec, dict) else visual_spec
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
        x_data = spec_dict.get("x", [1, 2, 3, 4, 5, 6, 7, 8])
        y_data = spec_dict.get("y", [2, 4, 8, 16, 32, 64, 128, 256])
        xlabel = spec_dict.get("xlabel", "Input X")
        ylabel = spec_dict.get("ylabel", "Output Y")

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
