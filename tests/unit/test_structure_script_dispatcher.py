"""Deep Unit Test Suite: Script-Agnostic Multilingual Dispatcher & Bengali Support.

Addresses Issue 3 from 01_rag_module_fix_plan_v2.md:
1. Multi-Script Headings: Validates Bengali, Devanagari, and Latin chapter heading recognizers.
2. Universal Indic Numeral Normalization: Validates conversion of Bengali [০-৯] and Devanagari [०-९] digits.
3. Language Detection: Validates automatic classification of Bengali (bn), Hindi (hi), and English (en).
4. Stopword-Filtered Key Term Extraction: Validates TF-IDF domain term extraction across Bengali and Hindi.
5. Extensibility & Fallback: Validates that unhandled scripts (Tamil, Telugu) gracefully fall back without crash.
"""

import pytest
from modules.rag.src.parsing.structure import (
    detect_language,
    is_chapter_or_section_heading,
    extract_chapters_from_text,
    extract_key_terms_tfidf,
    normalize_indic_numerals,
    SCRIPT_HEADING_REGISTRY,
)


class TestStructureScriptDispatcher:
    """Comprehensive test suite for script-agnostic document structure extraction."""

    # =========================================================================
    # 1. BENGALI CHAPTER HEADING RECOGNITION (NCERT & State Board Format)
    # =========================================================================

    BENGALI_HEADING_CASES = [
        ("অধ্যায় ১: গতি ও বলের প্রাথমিক সূত্রাবলী", True, "অধ্যায় ১: গতি ও বলের প্রাথমিক সূত্রাবলী"),
        ("পাঠ ২ - পদার্থের ভৌত ও রাসায়নিক অবস্থা", True, "পাঠ ২ - পদার্থের ভৌত ও রাসায়নিক অবস্থা"),
        ("একক ৩: তড়িৎপ্রবাহ ও বর্তনী নকশা", True, "একক ৩: তড়িৎপ্রবাহ ও বর্তনী নকশা"),
        ("পর্ব ৪: জীবনের মৌলিক একক ও কোষ", True, "পর্ব ৪: জীবনের মৌলিক একক ও কোষ"),
        ("বিভাগ ৫: পরমাণুর গঠন ও তেজস্ক্রিয়তা", True, "বিভাগ ৫: পরমাণুর গঠন ও তেজস্ক্রিয়তা"),
        ("অংশ ৬: পরিবেশ ও তার জৈব উপাদান", True, "অংশ ৬: পরিবেশ ও তার জৈব উপাদান"),
        ("অধ্যায় ১০: আলোকবিজ্ঞান ও লেন্সের সূত্র", True, "অধ্যায় ১০: আলোকবিজ্ঞান ও লেন্সের সূত্র"),
        ("সাধারণ কোনো বাক্য যা কোনো অধ্যায়ের শিরোনাম নয়।", False, None),
    ]

    @pytest.mark.parametrize("line,expected_is_heading,expected_title", BENGALI_HEADING_CASES)
    def test_bengali_chapter_headings_detected(self, line, expected_is_heading, expected_title):
        """Validates that Bengali textbook chapter markers are correctly classified."""
        is_h, title = is_chapter_or_section_heading(line)
        assert is_h is expected_is_heading
        if expected_is_heading:
            assert title == expected_title

    # =========================================================================
    # 2. DEVANAGARI CHAPTER HEADING RECOGNITION (NCERT Hindi Format)
    # =========================================================================

    DEVANAGARI_HEADING_CASES = [
        ("अध्याय १: प्रकाश-परावर्तन तथा अपवर्तन", True, "अध्याय १: प्रकाश-परावर्तन तथा अपवर्तन"),
        ("पाठ २ - अम्ल, क्षारक एवं लवण", True, "पाठ २ - अम्ल, क्षारक एवं लवण"),
        ("इकाई ३: धातु एवं अधातु", True, "इकाई ३: धातु एवं अधातु"),
        ("प्रकरण ४: कार्बन एवं उसके यौगिक", True, "प्रकरण ४: कार्बन एवं उसके यौगिक"),
        ("खण्ड ५: तत्वों का आवर्त वर्गीकरण", True, "खण्ड ५: तत्वों का आवर्त वर्गीकरण"),
        ("भाग ६: जैव प्रक्रम", True, "भाग ६: जैव प्रक्रम"),
        ("अध्याय १२: विद्युत धारा के चुंबकीय प्रभाव", True, "अध्याय १२: विद्युत धारा के चुंबकीय प्रभाव"),
        ("यह पाठ्यपुस्तक का एक सामान्य अनुच्छेद है।", False, None),
    ]

    @pytest.mark.parametrize("line,expected_is_heading,expected_title", DEVANAGARI_HEADING_CASES)
    def test_devanagari_chapter_headings_detected(self, line, expected_is_heading, expected_title):
        """Validates that Devanagari textbook chapter markers are correctly classified."""
        is_h, title = is_chapter_or_section_heading(line)
        assert is_h is expected_is_heading
        if expected_is_heading:
            assert title == expected_title

    # =========================================================================
    # 3. LATIN CHAPTER HEADING RECOGNITION (Standard STEM Format)
    # =========================================================================

    LATIN_HEADING_CASES = [
        ("Chapter 1: Electric Charges and Fields", True, "Chapter 1: Electric Charges and Fields"),
        ("Unit 2: Current Electricity and Circuits", True, "Unit 2: Current Electricity and Circuits"),
        ("Section 3: Magnetic Effects of Electric Current", True, "Section 3: Magnetic Effects of Electric Current"),
        ("Part IV: Electromagnetic Induction and Waves", True, "Part IV: Electromagnetic Induction and Waves"),
        ("Module 5: Semiconductor Electronics and Logic Gates", True, "Module 5: Semiconductor Electronics and Logic Gates"),
        ("2.1 Ohm's Law and Temperature Dependence", True, "2.1 Ohm's Law and Temperature Dependence"),
        ("ELECTRIC CIRCUITS AND RESISTANCE", True, "ELECTRIC CIRCUITS AND RESISTANCE"),
        ("This is just a regular body paragraph discussing physics principles.", False, None),
    ]

    @pytest.mark.parametrize("line,expected_is_heading,expected_title", LATIN_HEADING_CASES)
    def test_latin_chapter_headings_detected(self, line, expected_is_heading, expected_title):
        """Validates that Latin/English chapter markers and numbered subheadings are classified."""
        is_h, title = is_chapter_or_section_heading(line)
        assert is_h is expected_is_heading
        if expected_is_heading:
            assert title == expected_title

    # =========================================================================
    # 4. UNIVERSAL INDIC NUMERAL NORMALIZATION
    # =========================================================================

    @pytest.mark.parametrize("indic_str,expected_ascii", [
        ("অধ্যায় ১", "অধ্যায় 1"),
        ("অধ্যায় ৫", "অধ্যায় 5"),
        ("অধ্যায় ১০", "অধ্যায় 10"),
        ("অধ্যায় ৯৮৭", "অধ্যায় 987"),
        ("अध्याय १", "अध्याय 1"),
        ("अध्याय ५", "अध्याय 5"),
        ("अध्याय १०", "अध्याय 10"),
        ("अध्याय ९८७", "अध्याय 987"),
        ("০১২৩৪৫৬৭৮৯", "0123456789"),
        ("०१२३४५६७८९", "0123456789"),
    ])
    def test_universal_indic_numeral_normalization(self, indic_str, expected_ascii):
        """Verifies normalization of Bengali and Devanagari numeral characters to ASCII digits."""
        assert normalize_indic_numerals(indic_str) == expected_ascii

    # =========================================================================
    # 5. MULTILINGUAL LANGUAGE DETECTION
    # =========================================================================

    def test_multilingual_language_detection(self):
        """Validates primary language detection for Bengali, Hindi, and English."""
        bengali_sample = "কোনো পরিবাহীর মধ্য দিয়ে প্রবাহিত তড়িৎপ্রবাহ তার দুই প্রান্তের বিভবপ্রভেদের সমানুপাতিক।"
        hindi_sample = "किसी बंद परिपथ में प्रेरित विद्युत वाहक बल चुंबकीय फ्लक्स के परिवर्तन की दर के समानुपाती होता है।"
        english_sample = "The electric potential difference between two points is defined as work done per unit charge."

        assert detect_language(bengali_sample) == "bn"
        assert detect_language(hindi_sample) == "hi"
        assert detect_language(english_sample) == "en"
        assert detect_language("") == "en"
        assert detect_language("hi") == "en"  # Too short, falls back to default

    # =========================================================================
    # 6. BENGALI TF-IDF KEY TERM EXTRACTION WITH STOPWORD FILTERING
    # =========================================================================

    BENGALI_TEXTBOOK_CHAPTER = """
    অধ্যায় ১: তড়িৎপ্রবাহ এবং ওহমের সূত্রাবলী

    তড়িৎপ্রবাহ কোনো পরিবাহীর মধ্য দিয়ে আধান প্রবাহের পরিমাপ।
    কোনো পরিবাহীর মধ্য দিয়ে একক সময়ে যে পরিমাণ তড়িৎ আধান প্রবাহিত হয়, তাকে তড়িৎপ্রবাহ বলা হয়।
    আন্তর্জাতিক এস.আই পদ্ধতিতে তড়িৎপ্রবাহের একক অ্যাম্পিয়ার (Ampere)।
    বিভবপ্রভেদ হলো এমন এক বৈদ্যুতিক চাপ যা পরিবাহীর মধ্য দিয়ে ইলেকট্রন প্রবাহ নিশ্চিত করে।
    জর্জ সাইমন ওহম ১৮২৭ সালে প্রমাণ করেন যে, তাপমাত্রা অপরিবর্তিত থাকলে পরিবাহীর মধ্য দিয়ে প্রবাহিত কারেন্ট দুই প্রান্তের বিভবপ্রভেদের সমানুপাতিক।
    গাণিতিক সমীকরণ হলো: V = I * R, যেখানে R হলো পরিবাহীর রোধ (Resistance)।
    রোধ পরিবাহীর দৈর্ঘ্য, প্রস্থচ্ছেদের ক্ষেত্রফল এবং উপাদানের আপেক্ষিক রোধের ওপর সরাসরি নির্ভরশীল।
    জুলের সূত্রানুসারে পরিবাহীতে উৎপন্ন তাপীয় শক্তি H = I^2 * R * t।
    """

    def test_bengali_tfidf_key_term_extraction(self):
        """Validates TF-IDF key term extraction in Bengali with stopword rejection."""
        key_terms = extract_key_terms_tfidf(self.BENGALI_TEXTBOOK_CHAPTER, top_n=10)
        assert len(key_terms) >= 5

        # Key technical terms must be extracted
        terms_joined = " ".join(key_terms)
        assert any(term in terms_joined for term in ["তড়িৎপ্রবাহ", "বিভবপ্রভেদ", "রোধ", "অ্যাম্পিয়ার", "ওহম"])

        # Stopwords must be strictly filtered out
        bengali_stopwords = SCRIPT_HEADING_REGISTRY["bengali"]["stopwords"]
        for term in key_terms:
            assert term not in bengali_stopwords, f"Bengali stopword leaked into key terms: {term}"

    # =========================================================================
    # 7. MULTILINGUAL CHAPTER EXTRACTION PIPELINE
    # =========================================================================

    def test_extract_chapters_from_full_bengali_document(self):
        """Scans a full multi-chapter Bengali document and extracts chapters in chronological order."""
        full_doc = """
        অধ্যায় ১: স্থৈতিক তড়িৎ ও কুলম্বের সূত্র
        এখানে কুলম্বের সূত্রের ব্যাখ্যা দেওয়া হয়েছে।
        
        অধ্যায় ২: চলতড়িৎ ও ওহমের সূত্র
        এখানে কারেন্ট এবং রোধের পরিমাপ করা হয়েছে।
        
        অধ্যায় ৩: তড়িৎচৌম্বকীয় আবেশ ও ফ্যারাডের সূত্র
        এখানে আবেশ ও ট্রান্সফরমারের নীতি আলোচনা করা হয়েছে।
        """
        chapters = extract_chapters_from_text(full_doc)
        assert len(chapters) == 3
        assert chapters[0] == "অধ্যায় ১: স্থৈতিক তড়িৎ ও কুলম্বের সূত্র"
        assert chapters[1] == "অধ্যায় ২: চলতড়িৎ ও ওহমের সূত্র"
        assert chapters[2] == "অধ্যায় ৩: তড়িৎচৌম্বকীয় আবেশ ও ফ্যারাডের সূত্র"

    # =========================================================================
    # 8. SCRIPT DISPATCHER EXTENSIBILITY & UNHANDLED SCRIPT FALLBACK
    # =========================================================================

    def test_unhandled_indic_script_graceful_fallback(self):
        """Validates that unhandled Indic scripts (e.g. Tamil, Telugu) do not crash the system."""
        tamil_text = "அத்தியாயம் 1: மின்னோட்டம் மற்றும் மின்சுற்றுகள்\nமின்னோட்டம் என்பது ஒரு கடத்தியில் மின்னூட்டங்களின் ஓட்டமாகும்."
        telugu_text = "అధ్యాయం 1: విద్యుత్ ప్రవాహం మరియు సర్క్యూట్లు\nవిద్యుత్ ప్రవాహం అనగా వాహకంలో ఆవేశాల ప్రవాహ రేటు."

        # Should parse cleanly without raising AttributeError or RegexError
        tamil_chapters = extract_chapters_from_text(tamil_text)
        telugu_chapters = extract_chapters_from_text(telugu_text)
        tamil_terms = extract_key_terms_tfidf(tamil_text)
        telugu_terms = extract_key_terms_tfidf(telugu_text)

        assert isinstance(tamil_chapters, list)
        assert isinstance(telugu_chapters, list)
        assert isinstance(tamil_terms, list)
        assert isinstance(telugu_terms, list)
