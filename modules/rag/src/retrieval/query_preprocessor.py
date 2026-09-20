"""Query preprocessing and normalization for improved retrieval quality.

Normalizes raw user/orchestration queries before embedding to improve
dense and sparse retrieval recall.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Indic numeral → ASCII conversion (reused from structure.py for consistency)
_INDIC_NUMERAL_MAP = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9',
}

# Common question prefixes that add noise to embedding but no semantic value
_NOISE_PREFIXES = [
    r'^(please\s+)?(explain|tell\s+me\s+about|what\s+is|describe|define)\s+',
    r'^(mujhe\s+batao|samjhao|kya\s+hai|bataye)\s+',  # Hindi
    r'^(আমাকে\s+বলো|ব্যাখ্যা\s+করো|কি)\s+',  # Bengali
]

# Stop words that hurt dense embedding quality for short queries
_QUERY_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "for",
    "and", "or", "but", "it", "its", "this", "that", "with", "on", "at",
    "by", "from", "as", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "can", "shall", "about", "what", "how", "why", "when",
    "where", "which", "who", "whom", "please", "tell", "me", "explain",
}


def normalize_indic_numerals(text: str) -> str:
    """Convert Devanagari and Bengali native numerals to ASCII digits."""
    return "".join(_INDIC_NUMERAL_MAP.get(ch, ch) for ch in text)


def preprocess_query(
    query: str,
    strip_noise_prefixes: bool = True,
    expand_short_queries: bool = True,
    min_expansion_words: int = 2
) -> str:
    """Normalize and preprocess a retrieval query for improved recall.

    Steps:
    1. Strip leading/trailing whitespace and collapse internal whitespace
    2. Normalize Indic numerals to ASCII
    3. Optionally strip conversational noise prefixes
    4. Optionally expand very short queries (1-2 words) for better dense retrieval

    Args:
        query: Raw query string from the user or orchestration layer.
        strip_noise_prefixes: Remove common question prefixes that add noise.
        expand_short_queries: Pad single-word queries with context for embedding.
        min_expansion_words: Queries with fewer words than this get expanded.

    Returns:
        Normalized query string ready for embedding.
    """
    if not query or not query.strip():
        return ""

    # 1. Whitespace normalization
    normalized = re.sub(r'\s+', ' ', query.strip())

    # 2. Indic numeral normalization
    normalized = normalize_indic_numerals(normalized)

    # 3. Strip noise prefixes (optional)
    if strip_noise_prefixes:
        for pattern in _NOISE_PREFIXES:
            cleaned = re.sub(pattern, '', normalized, flags=re.IGNORECASE).strip()
            if cleaned and len(cleaned) >= 3:
                normalized = cleaned
                break

    # 4. Short query expansion (optional)
    if expand_short_queries:
        words = [w for w in normalized.split() if w.lower() not in _QUERY_STOPWORDS]
        if 0 < len(words) < min_expansion_words:
            # Add pedagogical context for single-concept queries
            normalized = f"{normalized} concept explanation definition"

    return normalized.strip()


def extract_key_query_terms(query: str) -> list[str]:
    """Extract semantically significant terms from a query for sparse matching boost.

    Filters stopwords and returns content-bearing tokens.
    """
    words = re.findall(r'[\w\u0900-\u097F\u0980-\u09FF]+', query.lower())
    return [w for w in words if w not in _QUERY_STOPWORDS and len(w) > 1]
