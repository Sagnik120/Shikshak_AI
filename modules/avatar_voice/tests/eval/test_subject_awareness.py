"""
Evaluation tests for Subject-Awareness Visual Synthesis.
Asserts that equation, code, diagram, and image render distinct visual assets
and do NOT collapse into identical generic stock templates.
"""

import os
import numpy as np
from PIL import Image
import pytest
from modules.avatar_voice.src.visuals import VisualRendererFactory


def test_subject_awareness_visual_distinctness(temp_output_dir):
    """
    Assert that different visual types (equation, code, diagram, map)
    produce distinct image outputs with measurable pixel-level diversity.
    """
    factory = VisualRendererFactory(output_dir=temp_output_dir)

    res_eq = factory.render({
        "type": "equation",
        "content": "\\nabla \\cdot \\mathbf{E} = \\frac{\\rho}{\\varepsilon_0}",
    })
    res_code = factory.render({
        "type": "code",
        "content": {"code": "def quicksort(arr):\n    return arr", "language": "python"},
    })
    res_diag = factory.render({
        "type": "diagram",
        "content": {"nodes": ["Start", "Process", "Decision", "End"]},
    })
    res_img = factory.render({
        "type": "image",
        "content": "Biological Cell Structure",
    })

    assert res_eq.visual_type == "equation"
    assert res_code.visual_type == "code"
    assert res_diag.visual_type == "diagram"
    assert res_img.visual_type == "image"

    img_eq = np.array(Image.open(res_eq.image_path).convert("L"))
    img_code = np.array(Image.open(res_code.image_path).convert("L"))
    img_diag = np.array(Image.open(res_diag.image_path).convert("L"))
    img_img = np.array(Image.open(res_img.image_path).convert("L"))

    # Compute mean absolute pixel difference across pairs
    diff_eq_code = np.mean(np.abs(img_eq.astype(float) - img_code.astype(float)))
    diff_eq_diag = np.mean(np.abs(img_eq.astype(float) - img_diag.astype(float)))
    diff_diag_img = np.mean(np.abs(img_diag.astype(float) - img_img.astype(float)))

    # Assert significant pixel difference across distinct templates
    assert diff_eq_code > 2.0, f"Equation and Code visuals are too similar ({diff_eq_code})"
    assert diff_eq_diag > 2.0, f"Equation and Diagram visuals are too similar ({diff_eq_diag})"
    assert diff_diag_img > 2.0, f"Diagram and Image visuals are too similar ({diff_diag_img})"
