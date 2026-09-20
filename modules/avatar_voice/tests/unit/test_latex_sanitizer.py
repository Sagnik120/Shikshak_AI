"""Offline tests for the equation-board LaTeX sanitizer (no rendering, no network)."""
import pytest

from modules.avatar_voice.src.visuals.latex_sanitizer import sanitize_latex, to_plain_text

SAMPLES = [
    "F = ma",
    r"\sum F = 0",
    r"\frac{\Delta v}{\Delta t}",
    r"\vec{F}_{net} = 0",
    r"\\frac{1}{2}mv^2",       # double-escaped by a JSON round trip
    r"$$E = mc^2$$",
    r"\(a^2 + b^2 = c^2\)",
    "```latex\nF = ma\n```",
    r"\thisisnotarealcommand{",  # invalid
]


@pytest.mark.parametrize("raw", SAMPLES)
def test_plain_text_never_leaks_latex(raw):
    out = to_plain_text(raw)
    assert "\\" not in out
    assert "$" not in out
    assert "```" not in out


def test_delimiters_are_stripped():
    assert sanitize_latex("$$E = mc^2$$") == "E = mc^2"
    assert sanitize_latex(r"\(a = b\)") == "a = b"
    assert sanitize_latex("latex: F = ma") == "F = ma"


def test_double_escaping_collapses():
    assert sanitize_latex(r"\\frac{a}{b}") == r"\frac{a}{b}"


def test_fraction_and_symbols_become_readable():
    assert to_plain_text(r"\frac{a}{b}") == "(a)/(b)"
    assert to_plain_text(r"\sum F = 0") == "Σ F = 0"
    assert "⃗" in to_plain_text(r"\vec{F} = 0")
    assert to_plain_text("E = mc^2") == "E = mc²"


def test_empty_input_is_empty():
    assert sanitize_latex(None) == ""
    assert to_plain_text("") == ""
