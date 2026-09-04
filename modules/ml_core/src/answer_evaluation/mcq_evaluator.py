def evaluate_mcq(raw_answer: str, expected_concept: str) -> bool:
    """
    Evaluate an MCQ response using deterministic EXACT string matching.
    Case-insensitive and whitespace-trimmed. NO fuzzy matching.
    """
    clean_answer = raw_answer.strip().lower()
    clean_expected = expected_concept.strip().lower()
    return clean_answer == clean_expected
