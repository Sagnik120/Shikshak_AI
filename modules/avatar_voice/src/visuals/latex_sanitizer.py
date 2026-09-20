"""
LaTeX input sanitizing for the equation board.

Models hand us formulas wrapped in `$$`, in markdown fences, or double-escaped
by a JSON round trip. Rendering those verbatim put raw backslashes on the board,
so every equation string passes through here first, and anything mathtext still
cannot parse falls back to a Unicode plain-text form.
"""

import re

# Only the sequences that actually show up in school-level formulas.
_SYMBOLS = {
    r"\Sigma": "Σ", r"\sum": "Σ", r"\Delta": "Δ", r"\delta": "δ",
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\theta": "θ",
    r"\lambda": "λ", r"\mu": "μ", r"\pi": "π", r"\rho": "ρ",
    r"\omega": "ω", r"\Omega": "Ω", r"\cdot": "·", r"\times": "×",
    r"\div": "÷", r"\pm": "±", r"\approx": "≈", r"\neq": "≠",
    r"\leq": "≤", r"\geq": "≥", r"\rightarrow": "→", r"\to": "→",
    r"\infty": "∞", r"\sqrt": "√", r"\int": "∫", r"\partial": "∂",
}

_SUPERSCRIPTS = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
                 "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}
_SUBSCRIPTS = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
               "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"}


def sanitize_latex(raw) -> str:
    """Strip delimiters, fences and JSON double-escaping from an equation string."""
    text = str(raw or "").strip()
    if not text:
        return ""

    text = re.sub(r"```[a-zA-Z]*", "", text).replace("```", "")
    text = re.sub(r"^\s*latex\s*:\s*", "", text, flags=re.IGNORECASE)

    # A JSON round trip turns \frac into \\frac; collapse it before anything else.
    text = text.replace("\\\\", "\\")

    text = re.sub(r"^\$\$(.*?)\$\$$", r"\1", text, flags=re.DOTALL).strip()
    text = re.sub(r"^\$(.*?)\$$", r"\1", text, flags=re.DOTALL).strip()
    text = re.sub(r"^\\\((.*?)\\\)$", r"\1", text, flags=re.DOTALL).strip()
    text = re.sub(r"^\\\[(.*?)\\\]$", r"\1", text, flags=re.DOTALL).strip()

    return text.strip()


def to_plain_text(raw) -> str:
    """Readable Unicode rendering. A backslash sequence must never survive this."""
    text = sanitize_latex(raw)
    if not text:
        return ""

    text = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", text)
    # U+20D7 is the combining arrow that turns F into F⃗.
    text = re.sub(r"\\vec\s*\{([^{}]*)\}", "\\1" + "\u20D7", text)
    text = re.sub(r"\\(?:text|mathrm|mathbf|operatorname)\s*\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"√(\1)", text)

    for token, glyph in sorted(_SYMBOLS.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(token, glyph)

    # Digits become real super/subscripts; longer scripts just lose the marker.
    text = re.sub(r"\^\{?([0-9])\}?", lambda m: _SUPERSCRIPTS[m.group(1)], text)
    text = re.sub(r"_\{?([0-9])\}?", lambda m: _SUBSCRIPTS[m.group(1)], text)
    text = re.sub(r"_\{([^{}]*)\}", r"_\1", text)
    text = re.sub(r"\^\{([^{}]*)\}", r"^\1", text)

    # Anything left that still starts with a backslash is dropped, not displayed.
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = text.replace("\\", "").replace("{", "").replace("}", "")

    return re.sub(r"\s+", " ", text).strip()
