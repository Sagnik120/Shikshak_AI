"""Document structure detection, language identification, and TF-IDF key-term extraction."""

from __future__ import annotations

import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def detect_language(text: str, default: str = "en") -> str:
    """Detect the primary language of the text.

    Returns an ISO 639-1 code (e.g. 'en', 'hi', 'bn') or default.
    """
    if not text or len(text.strip()) < 10:
        return default
    
    total_alpha = len(re.findall(r'\w', text))
    if total_alpha > 0:
        # Check Bengali script (U+0980 to U+09FF)
        bengali_count = len(re.findall(r'[\u0980-\u09FF]', text))
        if (bengali_count / total_alpha) > 0.15:
            return "bn"

        # Check Devanagari script (U+0900 to U+097F) for Hindi
        devanagari_count = len(re.findall(r'[\u0900-\u097F]', text))
        if (devanagari_count / total_alpha) > 0.15:
            return "hi"

        # Check Tamil (U+0B80 to U+0BFF)
        tamil_count = len(re.findall(r'[\u0B80-\u0BFF]', text))
        if (tamil_count / total_alpha) > 0.15:
            return "ta"
    
    try:
        from langdetect import detect
        lang = detect(text)
        return str(lang)
    except Exception:
        return default


# Universal Indic Numeral Conversion Table
INDIC_NUMERAL_MAP = {
    # Devanagari numerals
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    # Bengali numerals
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9',
}


def normalize_indic_numerals(text: str) -> str:
    """Convert Devanagari and Bengali native numerals to standard ASCII digits 0-9."""
    return "".join(INDIC_NUMERAL_MAP.get(ch, ch) for ch in text)


# Script-Agnostic Heading Dispatcher Registry
SCRIPT_HEADING_REGISTRY = {
    "bengali": {
        "script_char_range": r'[\u0980-\u09FF]',
        "patterns": [
            r'^(অধ্যায়|পাঠ|একক|পর্ব|বিভাগ|অংশ)\s*([০-৯\d]+)?\s*[:\.\-]?\s*(.*)$',
        ],
        "stopwords": {
            "এবং", "ও", "বা", "এর", "থেকে", "হলো", "হয়", "করে", "করা", "জন্য",
            "একটি", "এই", "সেই", "তা", "কি", "কোনো", "যে", "সে", "হয়ে", "ছিল",
            "হতে", "পর", "বলা", "বলে", "থাকে", "আছে", "দিয়ে", "উপর", "সাথে"
        }
    },
    "devanagari": {
        "script_char_range": r'[\u0900-\u097F]',
        "patterns": [
            r'^(अध्याय|पाठ|इकाई|प्रकरण|भाग|खण्ड)\s*([०-९\d]+)?\s*[:\.\-]?\s*(.*)$',
        ],
        "stopwords": {
            "और", "का", "के", "की", "में", "से", "को", "पर", "है", "हैं", "था",
            "थी", "होता", "होती", "एक", "यह", "वह", "इस", "उस", "भी", "तो", "ने",
            "द्वारा", "लिए", "गया", "गई", "कहा", "कहे", "होते", "सकता", "सकती"
        }
    },
    "latin": {
        "script_char_range": r'[A-Za-z]',
        "patterns": [
            r'^(Chapter|Unit|Section|Part|Module)\s*([0-9IVXLCDM]+)?\s*[:\.\-]?\s*(.*)$',
            r'^(\d+(\.\d+)*)\s+([A-Za-z][\w\s\-\':,]{2,})$',
        ],
        "stopwords": {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
            "about", "against", "between", "into", "through", "during", "before", "after",
            "above", "below", "from", "up", "down", "is", "are", "was", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "this", "that",
            "these", "those", "it", "its", "as", "by", "of", "which", "who", "whom"
        }
    }
}


def is_chapter_or_section_heading(line: str) -> tuple[bool, Optional[str]]:
    """Determine whether a line represents a chapter or section heading across scripts.

    Supports Bengali, Devanagari, and Latin headings using the script-agnostic dispatcher.
    Returns (is_heading, cleaned_heading_title).
    """
    clean_line = line.strip()
    if not clean_line or len(clean_line) > 100:
        return False, None

    # Iterate through script dispatchers
    for script_name, config in SCRIPT_HEADING_REGISTRY.items():
        # Quick check if line contains characters of this script
        if re.search(config["script_char_range"], clean_line):
            for pattern in config["patterns"]:
                match = re.match(pattern, clean_line, re.IGNORECASE)
                if match:
                    return True, clean_line

    # Standalone Latin heading heuristic (e.g. "ELECTRIC CIRCUITS AND OHM'S LAW")
    if clean_line.isupper() and 3 < len(clean_line) < 60 and re.search(r'[A-Za-z]', clean_line):
        return True, clean_line

    return False, None


def extract_chapters_from_text(text: str) -> List[str]:
    """Scan raw text and extract chapter titles in order across all supported scripts."""
    chapters: List[str] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        is_heading, title = is_chapter_or_section_heading(line)
        if is_heading and title and title not in chapters:
            chapters.append(title)
    return chapters


def get_all_multilingual_stopwords() -> set[str]:
    """Aggregate stopwords across English, Hindi, and Bengali for TF-IDF filtering."""
    combined = set()
    for config in SCRIPT_HEADING_REGISTRY.values():
        combined.update(config["stopwords"])
    return combined


def extract_key_terms_tfidf(text: str, top_n: int = 15) -> List[str]:
    """Extract top-N key terms from document text using multilingual TF-IDF.

    Supports English, Devanagari (Hindi), and Bengali scripts with stopword filtering.
    """
    if not text or len(text.strip()) < 20:
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
        if len(paragraphs) < 2:
            paragraphs = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
        if len(paragraphs) < 2:
            paragraphs = [text]

        stopwords = get_all_multilingual_stopwords()

        # Unicode token pattern matching Latin, Devanagari, and Bengali tokens
        vectorizer = TfidfVectorizer(
            token_pattern=r'(?u)\b[\w\u0900-\u097F\u0980-\u09FF]{2,}\b',
            ngram_range=(1, 2),
            max_df=0.90,
            min_df=1,
            max_features=150
        )
        tfidf_matrix = vectorizer.fit_transform(paragraphs)
        feature_names = vectorizer.get_feature_names_out()

        mean_scores = tfidf_matrix.mean(axis=0).A1
        scored_terms = sorted(zip(feature_names, mean_scores), key=lambda x: x[1], reverse=True)

        key_terms = [
            term for term, score in scored_terms
            if len(term) > 2 and not term.isdigit() and term.lower() not in stopwords
        ][:top_n]

        return key_terms
    except Exception as e:
        logger.debug(f"TF-IDF key term extraction failed with sklearn ({e}), using frequency fallback.")
        return _fallback_key_terms(text, top_n)


def _fallback_key_terms(text: str, top_n: int = 15) -> List[str]:
    """Frequency-based fallback supporting Latin, Devanagari, and Bengali scripts."""
    stop_words = get_all_multilingual_stopwords()
    # Match Latin, Devanagari, and Bengali tokens
    words = re.findall(r'[\u0900-\u097F\u0980-\u09FF]{2,}|[a-zA-Z]{3,}', text.lower())
    counts: dict[str, int] = {}
    for w in words:
        if w not in stop_words and not w.isdigit():
            counts[w] = counts.get(w, 0) + 1

    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]
