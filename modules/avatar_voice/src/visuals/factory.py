"""
Visual Renderer Factory.
Routes incoming visual specifications to the corresponding specialized subject-aware renderer.
"""

from typing import Any, Dict, Optional, Union
from modules.avatar_voice.src.models import VisualRenderResult
from modules.avatar_voice.src.visuals.base import VisualRenderer
from modules.avatar_voice.src.visuals.code_renderer import CodeRenderer
from modules.avatar_voice.src.visuals.diagram_renderer import DiagramRenderer
from modules.avatar_voice.src.visuals.equation_renderer import EquationRenderer
from modules.avatar_voice.src.visuals.graph_renderer import GraphRenderer
from modules.avatar_voice.src.visuals.image_renderer import ImageRenderer
from modules.avatar_voice.src.visuals.map_renderer import MapRenderer
from modules.avatar_voice.src.visuals.timeline_renderer import TimelineRenderer


class VisualRendererFactory:
    """Factory and router for visual synthesis renderers."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir
        self.renderers: Dict[str, VisualRenderer] = {
            "equation": EquationRenderer(output_dir=output_dir),
            "graph": GraphRenderer(output_dir=output_dir),
            "diagram": DiagramRenderer(output_dir=output_dir),
            "code": CodeRenderer(output_dir=output_dir),
            "timeline": TimelineRenderer(output_dir=output_dir),
            "map": MapRenderer(output_dir=output_dir),
            "image": ImageRenderer(output_dir=output_dir),
            "simulation": DiagramRenderer(output_dir=output_dir),
        }

    def render(self, visual_spec: Union[Dict[str, Any], Any]) -> VisualRenderResult:
        """Route and execute rendering for the given visual specification."""
        v_type = "diagram"
        if isinstance(visual_spec, dict):
            v_type = visual_spec.get("type", "diagram").lower().strip()
        elif hasattr(visual_spec, "type"):
            v_type = getattr(visual_spec, "type", "diagram").lower().strip()

        renderer = self.renderers.get(v_type, self.renderers["diagram"])
        return renderer.render(visual_spec)
