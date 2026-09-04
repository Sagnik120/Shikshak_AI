"""Deterministic rules for mapping subject/concept types to visual types."""

# Contract §5 visual_types: equation|graph|diagram|code|image|timeline|map|simulation
SUBJECT_TO_VISUAL = {
    "math": "equation",
    "physics": "diagram",
    "biology": "diagram",
    "history": "timeline",
    "programming": "code",
    "geography": "map",
    "chemistry": "simulation"
}

CONCEPT_TO_VISUAL = {
    "formula": "equation",
    "algorithm": "code",
    "function": "graph",
    "structure": "diagram",
    "event": "timeline",
    "location": "map",
    "experiment": "simulation"
}

def get_rule_based_visual(subject: str, concept: str) -> str:
    """Attempt deterministic match, fallback to empty string if ambiguous."""
    subject = subject.lower().strip()
    concept = concept.lower().strip()
    
    # Concept type takes precedence if identified
    for key, val in CONCEPT_TO_VISUAL.items():
        if key in concept:
            return val
            
    # Fallback to subject
    if subject in SUBJECT_TO_VISUAL:
        return SUBJECT_TO_VISUAL[subject]
        
    return ""
