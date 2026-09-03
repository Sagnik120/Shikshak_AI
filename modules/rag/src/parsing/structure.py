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


# Devanagari and Latin heading pattern definitions
DEVANAGARI_HEADING_PATTERNS = [
    r'^(अध्याय|पाठ|इकाई|प्रकरण|भाग|खण्ड)\s*([०-९\d]+)?\s*[:\.\-]?\s*(.*)$',
]

LATIN_HEADING_PATTERNS = [
    r'^(Chapter|Unit|Section|Part|Module)\s*(\d+)?\s*[:\.\-]?\s*(.*)$',
    r'^(\d+(\.\d+)*)\s+([A-Za-z][\w\s\-]{2,})$',
]


def is_chapter_or_section_heading(line: str) -> tuple[bool, Optional[str]]:
    """Determine whether a line of text represents a chapter or section heading in Devanagari or Latin scripts.

    Returns:
        (is_heading, cleaned_heading_title)
    """
    clean_line = line.strip()
    if not clean_line or len(clean_line) > 100:
        return False, None

    # 1. Check Devanagari heading patterns (e.g. "अध्याय 1: गति के नियम", "पाठ 2")
    for pattern in DEVANAGARI_HEADING_PATTERNS:
        match = re.match(pattern, clean_line)
        if match:
            return True, clean_line

    # 2. Check Latin heading patterns (e.g. "Chapter 1: Motion", "Unit 2")
    for pattern in LATIN_HEADING_PATTERNS:
        match = re.match(pattern, clean_line, re.IGNORECASE)
        if match:
            return True, clean_line

    # 3. Short standalone heading heuristics
    if clean_line.isupper() and 3 < len(clean_line) < 60:
        return True, clean_line

    return False, None


def extract_chapters_from_text(text: str) -> List[str]:
    """Scan raw text and extract chapter titles in order across Devanagari and Latin scripts."""
    chapters: List[str] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        is_heading, title = is_chapter_or_section_heading(line)
        if is_heading and title and title not in chapters:
            chapters.append(title)
    return chapters


def extract_key_terms_tfidf(text: str, top_n: int = 15) -> List[str]:
    """Extract top-N key terms from the document text using TF-IDF.

    Per detailed_design.md §1: lightweight, deterministic, non-ML extraction supporting Latin and Devanagari.
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

        # Use token pattern supporting both Latin alphabetic and Devanagari scripts
        vectorizer = TfidfVectorizer(
            token_pattern=r'(?u)\b[\w\u0900-\u097F]{2,}\b',
            ngram_range=(1, 2),
            max_df=0.90,
            min_df=1,
            max_features=120
        )
        tfidf_matrix = vectorizer.fit_transform(paragraphs)
        feature_names = vectorizer.get_feature_names_out()
        
        # Aggregate mean score across chunks
        mean_scores = tfidf_matrix.mean(axis=0).A1
        scored_terms = sorted(zip(feature_names, mean_scores), key=lambda x: x[1], reverse=True)
        
        # Filter out purely numeric or single-char tokens
        key_terms = [
            term for term, score in scored_terms
            if len(term) > 2 and not term.isdigit()
        ][:top_n]

        return key_terms
    except Exception as e:
        logger.debug(f"TF-IDF key term extraction failed with sklearn ({e}), using frequency fallback.")
        return _fallback_key_terms(text, top_n)


def _fallback_key_terms(text: str, top_n: int = 15) -> List[str]:
    """Frequency-based fallback supporting both Latin and Devanagari text."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "about", "against", "between", "into", "through", "during", "before", "after",
        "above", "below", "from", "up", "down", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "this", "that",
        "these", "those", "it", "its", "as", "by", "of", "which", "who", "whom",
        # Common Hindi postpositions / functional words
        "और", "का", "के", "की", "में", "से", "को", "पर", "है", "हैं", "था", "थी",
        "होता", "होती", "एक", "यह", "वह", "इस", "उस", "भी", "तो", "ने"
    }
    # Match both Latin words and Devanagari words
    words = re.findall(r'[\u0900-\u097F]{2,}|[a-zA-Z]{3,}', text.lower())
    counts: dict[str, int] = {}
    for w in words:
        if w not in stop_words and not w.isdigit():
            counts[w] = counts.get(w, 0) + 1
            
    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]
