"""
Unit tests for specialized Visual Synthesis renderers and error fallbacks.
"""

import os
from PIL import Image
import pytest
from modules.avatar_voice.src.visuals import (
    CodeRenderer,
    DiagramRenderer,
    EquationRenderer,
    GraphRenderer,
    ImageRenderer,
    MapRenderer,
    TimelineRenderer,
    VisualRendererFactory,
)


def test_equation_renderer(temp_output_dir):
    """Verify equation renderer generates 1344x1080 mathematical slide."""
    renderer = EquationRenderer(output_dir=temp_output_dir)
    res = renderer.render({"type": "equation", "content": "\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}"})
    assert os.path.exists(res.image_path)
    assert res.width == 1344
    assert res.height == 1080
    assert res.visual_type == "equation"
    img = Image.open(res.image_path)
    assert img.size == (1344, 1080)


def test_equation_renderer_malformed_fallback(temp_output_dir):
    """Verify broken LaTeX syntax falls back to plain-text rendering without crashing."""
    renderer = EquationRenderer(output_dir=temp_output_dir)
    res = renderer.render({"type": "equation", "content": "\\invalid_broken_macro{{{{"})
    assert os.path.exists(res.image_path)
    assert res.visual_type == "equation"


def test_graph_renderer(temp_output_dir):
    """Verify line/bar chart rendering from structured spec."""
    renderer = GraphRenderer(output_dir=temp_output_dir)
    res = renderer.render({
        "type": "graph",
        "content": {"title": "Loss vs Epochs", "type": "line", "x": [1, 2, 3, 4], "y": [0.8, 0.5, 0.3, 0.15]},
    })
    assert os.path.exists(res.image_path)
    assert res.visual_type == "graph"


def test_diagram_renderer(temp_output_dir):
    """Verify process flowchart and node relationship rendering."""
    renderer = DiagramRenderer(output_dir=temp_output_dir)
    res = renderer.render({
        "type": "diagram",
        "content": {"nodes": ["Data Ingestion", "Embedding Model", "Vector Store", "LLM Generation"]},
    })
    assert os.path.exists(res.image_path)
    assert res.visual_type == "diagram"


def test_code_renderer(temp_output_dir):
    """Verify code snippet window with line numbers and optional terminal output."""
    renderer = CodeRenderer(output_dir=temp_output_dir)
    res = renderer.render({
        "type": "code",
        "content": {"code": "def binary_search(arr, x):\n    low, high = 0, len(arr) - 1\n    return -1", "language": "python", "output": "Index: 4"},
    })
    assert os.path.exists(res.image_path)
    assert res.visual_type == "code"


def test_timeline_renderer(temp_output_dir):
    """Verify chronological timeline milestone rendering."""
    renderer = TimelineRenderer(output_dir=temp_output_dir)
    res = renderer.render({
        "type": "timeline",
        "content": [{"step": "1947", "label": "Independence"}, {"step": "1950", "label": "Constitution"}],
    })
    assert os.path.exists(res.image_path)
    assert res.visual_type == "timeline"


def test_map_renderer(temp_output_dir):
    """Verify spatial map coordinate rendering."""
    renderer = MapRenderer(output_dir=temp_output_dir)
    res = renderer.render({
        "type": "map",
        "content": {"markers": [{"label": "City A", "x": 0.3, "y": 0.4}, {"label": "City B", "x": 0.7, "y": 0.6}]},
    })
    assert os.path.exists(res.image_path)
    assert res.visual_type == "map"


def test_image_renderer(temp_output_dir):
    """Verify conceptual image and card illustration renderer."""
    renderer = ImageRenderer(output_dir=temp_output_dir)
    res = renderer.render({"type": "image", "content": "Cellular Mitosis Overview"})
    assert os.path.exists(res.image_path)
    assert res.visual_type == "image"


def test_visual_renderer_factory_routing(temp_output_dir):
    """Verify factory routes all known types and falls back for simulation."""
    factory = VisualRendererFactory(output_dir=temp_output_dir)
    for v_type in ["equation", "graph", "diagram", "code", "timeline", "map", "image", "simulation"]:
        res = factory.render({"type": v_type, "content": "test"})
        assert os.path.exists(res.image_path)
