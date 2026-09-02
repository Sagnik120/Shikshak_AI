"""Citation extraction and hallucination risk signaling from LLM responses."""

from __future__ import annotations

import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


def parse_grounded_citations(
    llm_output_text: str,
    valid_candidate_ids: Optional[List[str]] = None
) -> Tuple[str, List[str], Optional[str]]:
    """Parse grounded_on chunk IDs from the LLM output and check for hallucination risk signals.

    Args:
        llm_output_text: Raw response string from the Explainer/Questioner Agent.
        valid_candidate_ids: List of chunk IDs that were provided in the prompt context.

    Returns:
        Tuple of (clean_explanation_text, cited_chunk_ids, risk_signal_or_none)
    """
    clean_text = llm_output_text.strip()
    cited_ids: List[str] = []
    risk_signal: Optional[str] = None

    # Match `grounded_on: [chunk_1, chunk_2]` pattern
    pattern = r'grounded_on:\s*\[(.*?)\]'
    match = re.search(pattern, clean_text, re.IGNORECASE)

    if match:
        raw_ids = match.group(1).split(",")
        cited_ids = [c.strip().strip("'\"") for c in raw_ids if c.strip().strip("'\"")]
        # Strip the grounded_on footer from the student-facing explanation text
        clean_text = re.sub(pattern, "", clean_text, flags=re.IGNORECASE).strip()

    # Hallucination-risk heuristic per detailed_design.md §6.3:
    # If candidate context was provided, but the model cited nothing OR cited hallucinated chunk IDs
    if valid_candidate_ids:
        valid_set = set(valid_candidate_ids)
        invalid_citations = [c for c in cited_ids if c not in valid_set]
        if invalid_citations:
            risk_signal = f"hallucinated_chunk_references: {invalid_citations}"
        elif not cited_ids and len(valid_candidate_ids) >= 2:
            # Model ignored provided document context
            risk_signal = "empty_citations_despite_available_context"

    return clean_text, cited_ids, risk_signal
