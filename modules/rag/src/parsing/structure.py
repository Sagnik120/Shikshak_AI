"""Document structure detection, language identification, and TF-IDF key-term extraction."""

from __future__ import annotations

import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def detect_language(text: str, default: str = "en") -> str:
    """Detect the primary language of the text.

    Returns an ISO 639-1 code (e.g. 'en', 'hi') or default.
    """
    if not text or len(text.strip()) < 10:
        return default
    
    # Check for Devanagari script for Hindi
    devanagari_count = len(re.findall(r'[\u0900-\u097F]', text))
    total_alpha = len(re.findall(r'\w', text))
    if total_alpha > 0 and (devanagari_count / total_alpha) > 0.15:
        return "hi"
    
    try:
        from langdetect import detect
        lang = detect(text)
        return str(lang)
    except Exception:
        # Fallback to default
        return default


def extract_key_terms_tfidf(text: str, top_n: int = 15) -> List[str]:
    """Extract top-N key terms from the document text using TF-IDF.

    Per detailed_design.md §1: lightweight, deterministic, non-ML extraction.
    """
    if not text or len(text.strip()) < 20:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        # Split text into rough sentences/paragraphs to form a mini-corpus for TF-IDF
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
        if len(paragraphs) < 2:
            paragraphs = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
        
        if len(paragraphs) < 2:
            paragraphs = [text]

        vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_df=0.85,
            min_df=1,
            stop_words="english",
            max_features=100
        )
        tfidf_matrix = vectorizer.fit_transform(paragraphs)
        feature_names = vectorizer.get_feature_names_out()
        
        # Aggregate mean score across chunks
        mean_scores = tfidf_matrix.mean(axis=0).A1
        scored_terms = sorted(zip(feature_names, mean_scores), key=lambda x: x[1], reverse=True)
        
        # Filter out purely numeric or short tokens
        key_terms = [
            term for term, score in scored_terms
            if len(term) > 2 and not term.isdigit()
        ][:top_n]

        return key_terms
    except Exception as e:
        logger.debug(f"TF-IDF key term extraction failed with sklearn ({e}), using frequency fallback.")
        return _fallback_key_terms(text, top_n)


def _fallback_key_terms(text: str, top_n: int = 15) -> List[str]:
    """Frequency-based fallback when sklearn is not available."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "about", "against", "between", "into", "through", "during", "before", "after",
        "above", "below", "from", "up", "down", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "this", "that",
        "these", "those", "it", "its", "as", "by", "of", "which", "who", "whom"
    }
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    counts: dict[str, int] = {}
    for w in words:
        if w not in stop_words:
            counts[w] = counts.get(w, 0) + 1
            
    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]
