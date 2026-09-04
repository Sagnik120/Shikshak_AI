import re
from typing import List
from collections import Counter
from modules.ml_core.src.concept_extraction.config import TOP_K_CONCEPTS, MIN_WORD_LENGTH

class ConceptExtractor:
    """
    Lightweight, zero-LLM key-term extractor.
    Uses term frequency heuristic to identify top concepts from parsed chunks.
    """
    
    def __init__(self):
        # A minimal list of english stopwords to avoid heavy dependencies like NLTK
        self.stopwords = {
            "the", "and", "for", "with", "from", "that", "this", "these", "those",
            "which", "who", "whom", "whose", "what", "where", "when", "why", "how",
            "all", "any", "both", "each", "few", "more", "most", "other", "some",
            "such", "nor", "not", "only", "own", "same", "than", "too", "very",
            "can", "will", "just", "should", "now", "are", "was", "were", "been",
            "have", "has", "had", "doing", "does", "did", "out", "about", "into"
        }

    def extract(self, chunk_texts: List[str], top_k: int = TOP_K_CONCEPTS) -> List[str]:
        """
        Extract top key terms from the given list of text chunks.
        """
        word_counts = Counter()
        
        for text in chunk_texts:
            # Simple tokenization: alphabetic words of length >= MIN_WORD_LENGTH
            words = re.findall(rf'\b[a-zA-Z]{{{MIN_WORD_LENGTH},}}\b', text.lower())
            for w in words:
                if w not in self.stopwords:
                    word_counts[w] += 1
                    
        # Return the top K words
        return [word for word, count in word_counts.most_common(top_k)]

# Singleton instance
_extractor = ConceptExtractor()

def extract_concepts(chunk_texts: List[str], top_k: int = TOP_K_CONCEPTS) -> List[str]:
    """Helper function to extract concepts using the singleton extractor."""
    return _extractor.extract(chunk_texts, top_k)
