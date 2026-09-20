import re
import unicodedata


def _normalise(text: str) -> str:
    """Lowercase, strip accents/punctuation, and collapse whitespace.

    MCQ options come back from the LLM with inconsistent trailing periods and
    option prefixes ("B) ..."), so a raw equality check rejects answers that
    are in fact identical to the expected option.
    """
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    # Drop a leading option label such as "a)", "(b.", "3 -".
    text = re.sub(r"^\(?\s*[a-d0-9]\s*[\).:-]\s+", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def evaluate_mcq(raw_answer: str, expected_concept: str) -> bool:
    """Deterministic MCQ match: normalised equality, with no fuzzy scoring."""
    answer = _normalise(raw_answer)
    expected = _normalise(expected_concept)
    if not answer or not expected:
        return False
    return answer == expected
