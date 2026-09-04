"""Deep Unit Test Suite: Chunker Real Token Ground-Truth & Indic Subword Budgeting.

Addresses Issue 2 from 01_rag_module_fix_plan_v2.md:
1. Ground-Truth Token Budget: Validates that chunks never exceed the Contract §4 ceiling
   of 500 tokens under heavy Sanskritized conjunct expansion.
2. Code-Mixed Hinglish: Validates that texts with < 15% Devanagari characters
   (inline English code terms) correctly account for Indic subword expansion without budget overflow.
3. Bengali Science Text: Validates Bengali Unicode subword token budgeting.
4. Trailing Merge Guard: Verifies that merging trailing chunks never pushes total tokens > 500.
5. Extreme Boundary: Massive monolithic 2000-word paragraph without punctuation delimiters
   decomposes cleanly into <= 500 token chunks.
"""

import pytest
from modules.rag.src.models import RawSection
from modules.rag.src.chunking.chunker import (
    count_tokens,
    split_text_into_token_chunks,
    chunk_sections,
    finalize_and_verify_chunks,
    get_tokenizer,
)


@pytest.fixture(scope="module")
def tokenizer():
    return get_tokenizer()


class TestChunkerRealTokenGroundTruth:
    """Comprehensive test suite verifying chunk token budgets across scripts and edge cases."""

    # =========================================================================
    # 1. HEAVY SANSKRITIZED HINDI PHYSICS TEXT (Dense Conjunct Consonants)
    # =========================================================================

    SANSKRITIZED_HINDI_PHYSICS = """
    विद्युत्-चुम्बकीय प्रेरण और प्रत्यावर्ती धारा के सिद्धान्त भौतिक विज्ञान के आधारभूत स्तम्भ हैं।
    जब किसी बन्द परिपथ से सम्बद्ध चुम्बकीय फ्लक्स में परिवर्तन होता है, तो परिपथ में एक प्रेरित विद्युत्-वाहक बल उत्पन्न होता है।
    फैराडे के विद्युत्-चुम्बकीय प्रेरण सम्बन्धी प्रथम नियमानुसार, प्रेरित विद्युत्-वाहक बल का परिमाण चुम्बकीय फ्लक्स के परिवर्तन की समय-दर के अनुक्रमानुपाती होता है।
    लेंज़ का नियम ऊर्जा संरक्षण के सार्वत्रिक सिद्धान्त पर आधारित है, जिसके अनुसार प्रेरित धारा की दिशा सदैव ऐसी होती है कि वह उस कारण का विरोध करती है जिससे वह स्वयं उत्पन्न होती है।
    स्वप्रेरण गुणांक अथवा स्वप्रेरकत्व किसी कुण्डली का वह विशिष्ट गुणधर्म है जो उसमें प्रवाहित धारा के मान में किसी भी प्रकार के परिवर्तन का विरोध करता है।
    पारस्परिक प्रेरण की घटना में, प्राथमिक कुण्डली में धारा परिवर्तन करने पर द्वितीयक कुण्डली में फ्लक्स परिवर्तन के कारण प्रेरित विभव उत्पन्न हो जाता है।
    प्रत्यावर्ती धारा परिपथों में संधारित्र, प्रेरकत्व तथा प्रतिरोध के संयुक्त प्रभाव को प्रतिबाधा कहते हैं।
    अनुनाद की स्थिति में परिपथ की प्रतिबाधा न्यूनतम तथा धारा का आयाम अधिकतम हो जाता है।
    विद्युत्-चुम्बकीय दोलनों में ऊर्जा का स्थानान्तरण वैद्युत क्षेत्र तथा चुम्बकीय क्षेत्र के मध्य निरन्तर होता रहता है।
    ट्रांसफॉर्मर अन्योन्य प्रेरण के सिद्धान्त पर कार्य करने वाला एक स्थैतिक विद्युत् उपकरण है जो उच्च विभव वाली निम्न धारा को निम्न विभव वाली उच्च धारा में रूपान्तरित करता है।
    """ * 6  # ~1500 words, rich in conjunct consonants

    def test_sanskritized_hindi_never_exceeds_500_tokens(self, tokenizer):
        """Heavy conjunct consonants must never breach the 500-token ceiling in any emitted chunk."""
        chunks = split_text_into_token_chunks(
            self.SANSKRITIZED_HINDI_PHYSICS,
            target_tokens=300,
            max_tokens=500,
            tokenizer=tokenizer
        )

        assert len(chunks) >= 3, f"Expected multi-chunk split, got {len(chunks)}"

        for idx, chunk in enumerate(chunks):
            real_tokens = count_tokens(chunk, tokenizer)
            assert real_tokens <= 500, (
                f"Chunk {idx} breached 500-token ceiling! Real token count: {real_tokens}\n"
                f"Chunk text snippet: {chunk[:80]}..."
            )
            assert real_tokens >= 50, (
                f"Chunk {idx} is an orphan under 50 tokens: {real_tokens}"
            )

    # =========================================================================
    # 2. CODE-MIXED HINGLISH CS TEXT (< 15% Devanagari Character Ratio)
    # =========================================================================

    HINGLISH_CS_TEXT = """
    Computer Science me binary search algorithm ek bohot hi efficient searching technique hai.
    Agar humare paas ek sorted array hai of size n, to linear search O(n) time complexity leta hai.
    Lekin binary search divide and conquer paradigm use karta hai jisme array ko repeatedly half me divide kiya jata hai.
    Har step par mid element calculate hota hai: mid = low + (high - low) // 2.
    Agar target value array[mid] ke barabar hai, to search successfully index return kar deta hai.
    Agar target value array[mid] se choti hai, to high = mid - 1 set karte hain kyunki target left subarray me hoga.
    Agar target value array[mid] se badi hai, to low = mid + 1 set karte hain kyunki target right subarray me hoga.
    Is recursive division ki wajah se binary search ki worst-case time complexity O(log n) hoti hai.
    Space complexity iterative approach me O(1) hoti hai aur recursive approach me call stack ki wajah se O(log n) hoti hai.
    Real-world software engineering me databases, indexing engines, aur standard libraries binary search use karti hain.
    Python me bisect module provide karta hai bisect_left aur bisect_right functions for efficient lookup in sorted lists.
    """ * 5  # Heavily mixed with English CS terminology

    def test_code_mixed_hinglish_low_devanagari_ratio_budgeting(self, tokenizer):
        """Hinglish text with < 15% Devanagari characters must still respect subword token budget."""
        chunks = split_text_into_token_chunks(
            self.HINGLISH_CS_TEXT,
            target_tokens=300,
            max_tokens=500,
            tokenizer=tokenizer
        )

        assert len(chunks) >= 2, "Expected multiple chunks for long Hinglish text"

        for idx, chunk in enumerate(chunks):
            real_tokens = count_tokens(chunk, tokenizer)
            assert real_tokens <= 500, (
                f"Hinglish Chunk {idx} exceeded 500 tokens: {real_tokens} tokens"
            )

    # =========================================================================
    # 3. BENGALI SCIENCE TEXT (NCERT Bengali-Medium Support)
    # =========================================================================

    BENGALI_PHYSICS_TEXT = """
    তড়িৎপ্রবাহ এবং ওহমের সূত্র পদার্থবিজ্ঞানের একটি অত্যন্ত গুরুত্বপূর্ণ মৌলিক অংশ।
    কোনো পরিবাহীর মধ্য দিয়ে প্রতি একক সময়ে যে পরিমাণ তড়িৎ আধান প্রবাহিত হয়, তাকে তড়িৎপ্রবাহ বা কারেন্ট বলে।
    তড়িৎপ্রবাহের এস.আই একক হলো অ্যাম্পিয়ার (Ampere)।
    পরিবাহীর দুই প্রান্তের বিভবপ্রভেদ বজায় রাখার জন্য একটি বাহ্যিক শক্তির উৎসের প্রয়োজন হয়, যাকে তড়িচ্চালক বল বলা হয়।
    জর্জ সাইমন ওহম ১৮২৭ সালে প্রমাণ করেন যে, তাপমাত্রা ও অন্যান্য ভৌত অবস্থা অপরিবর্তিত থাকলে, কোনো পরিবাহীর মধ্য দিয়ে প্রবাহিত তড়িৎপ্রবাহ ওই পরিবাহীর দুই প্রান্তের বিভবপ্রভেদের সমানুপাতিক।
    গাণিতিকভাবে, V = I * R, যেখানে R হলো পরিবাহীর রোধ (Resistance)।
    রোধ পরিবাহীর উপাদান, দৈর্ঘ্য এবং প্রস্থচ্ছেদের ক্ষেত্রফলের ওপর সরাসরি নির্ভর করে।
    পরিবাহীর দৈর্ঘ্য বৃদ্ধি পেলে রোধ বৃদ্ধি পায় এবং প্রস্থচ্ছেদের ক্ষেত্রফল বৃদ্ধি পেলে রোধ হ্রাস পায়।
    জুলের তাপীয় ক্রিয়ার সূত্রানুসারে, পরিবাহীতে উৎপন্ন তাপ H = I^2 * R * t।
    """ * 6

    def test_bengali_text_token_budget_guarantee(self, tokenizer):
        """Bengali textbook text must accurately chunk without exceeding 500 tokens."""
        chunks = split_text_into_token_chunks(
            self.BENGALI_PHYSICS_TEXT,
            target_tokens=300,
            max_tokens=500,
            tokenizer=tokenizer
        )

        assert len(chunks) >= 2

        for idx, chunk in enumerate(chunks):
            real_tokens = count_tokens(chunk, tokenizer)
            assert real_tokens <= 500, (
                f"Bengali Chunk {idx} exceeded 500 tokens: {real_tokens}"
            )

    # =========================================================================
    # 4. TRAILING CHUNK MERGE GUARD TEST
    # =========================================================================

    def test_trailing_merge_guard_never_overshoots_max_tokens(self, tokenizer):
        """Merging a small trailing fragment into the previous chunk must NEVER exceed 500 tokens."""
        # Create a text that would yield a 480-token first chunk and a 35-token tail chunk
        # If merged blindly, it would be 515 tokens (> 500). The guard must prevent this.
        base_sentence = "Electric potential difference drives the continuous flow of charges through a conductor. "
        # ~480 tokens
        chunk1_text = base_sentence * 34
        # ~35 tokens
        tail_text = "Resistance is measured in Ohms and depends on temperature and geometry."

        combined = f"{chunk1_text}\n\n{tail_text}"

        chunks = split_text_into_token_chunks(
            combined,
            target_tokens=300,
            max_tokens=500,
            min_chunk_tokens=50,
            tokenizer=tokenizer
        )

        for idx, c in enumerate(chunks):
            n_tokens = count_tokens(c, tokenizer)
            assert n_tokens <= 500, f"Trailing merge overshot max_tokens! Chunk {idx} has {n_tokens} tokens"

    # =========================================================================
    # 5. EXTREME MONOLITHIC PARAGRAPH WITHOUT PUNCTUATION
    # =========================================================================

    def test_monolithic_unpunctuated_text_decomposes_safely(self, tokenizer):
        """A continuous 1500-word run-on text with zero sentence delimiters must decompose safely."""
        words = ["current", "voltage", "resistance", "impedance", "conductance", "inductance", "capacitance"]
        monolithic_text = " ".join(words * 250)  # 1750 words, no periods

        chunks = split_text_into_token_chunks(
            monolithic_text,
            target_tokens=300,
            max_tokens=500,
            tokenizer=tokenizer
        )

        assert len(chunks) >= 4
        for idx, c in enumerate(chunks):
            n_tokens = count_tokens(c, tokenizer)
            assert n_tokens <= 500, f"Monolithic chunk {idx} exceeded 500 tokens: {n_tokens}"

    # =========================================================================
    # 6. STRUCTURE-AWARE RAW SECTION CHUNKING
    # =========================================================================

    def test_chunk_sections_preserves_metadata_and_respects_ceiling(self, tokenizer):
        """chunk_sections() must attach IDs, preserve section titles, and guarantee token ceilings."""
        sections = [
            RawSection(
                section_title="विद्युत् धारा और विभव",
                raw_text="विद्युत् धारा किसी चालक में आवेश के प्रवाह की दर है। " * 60,
                page_or_slide=1
            ),
            RawSection(
                section_title="ওহমের সূত্র ও রোধ",
                raw_text="ওহমের সূত্র অনুসারে বিভবপ্রভেদ এবং তড়িৎপ্রবাহ পরস্পর সমানুপাতিক। " * 60,
                page_or_slide=2
            )
        ]

        chunks = chunk_sections(
            sections=sections,
            document_id="doc_multilingual_test_123",
            target_tokens=300,
            max_tokens=500,
            tokenizer=tokenizer
        )

        assert len(chunks) >= 4

        for c in chunks:
            tokens = count_tokens(c.text, tokenizer)
            assert tokens <= 500, f"Section chunk {c.chunk_id} breached 500 tokens ({tokens})"
            assert c.section_title in ("विद्युत् धारा और विभव", "ওহমের সূত্র ও রোধ")
            assert c.page_or_slide in (1, 2)
            assert c.chunk_id.startswith("chunk_doc_mult")

    # =========================================================================
    # 7. REAL-WORLD NCERT BIOLOGY HINDI SECTION (Life Processes / जैव प्रक्रम)
    # =========================================================================

    NCERT_BIOLOGY_HINDI = """
    सजीवों में पोषण और श्वसन जीवन के रख-रखाव के लिए अनिवार्य जैव प्रक्रम हैं।
    स्वपोषी पोषण में जीव कार्बन डाइऑक्साइड और जल जैसे सरल अकार्बनिक पदार्थों को सूर्य के प्रकाश और क्लोरोफिल की उपस्थिति में कार्बोहाइड्रेट में परिवर्तित करते हैं।
    प्रकाश संश्लेषण की रासायनिक अभिक्रिया: 6CO2 + 12H2O -> C6H12O6 + 6O2 + 6H2O।
    विषमपोषी पोषण में अन्य जीवों द्वारा तैयार किए गए जटिल कार्बनिक पदार्थों का उपभोग किया जाता है।
    मानव पाचन तंत्र में आमाशय हाइड्रोक्लोरिक अम्ल स्रावित करता है जो पेप्सिन एंजाइम के कार्य के लिए अम्लीय माध्यम तैयार करता है।
    क्षुद्रांत्र (छोटी आंत) में कार्बोहाइड्रेट, वसा और प्रोटीन का पूर्ण पाचन होता है।
    श्वसन प्रक्रम में ग्लूकोज का विखंडन पाइरुवेट में होता है जो कोशिकाद्रव्य में संपन्न होता है।
    ऑक्सीजन की उपस्थिति में पाइरुवेट का विखंडन माइटोकॉन्ड्रिया में होता है तथा प्रचुर मात्रा में एटीपी (ATP) ऊर्जा विमुक्त होती है।
    रक्त परिसंचरण तंत्र में हृदय एक पेशीय अंग है जो पूरे शरीर में रुधिर को पंप करता है।
    वृक्क (Kidney) में नेफ्रॉन निस्यंदन की आधारभूत क्रियात्मक इकाई है जो उत्सर्जी अपशिष्ट पदार्थों को मूत्र के रूप में पृथक करती है।
    """ * 4

    def test_real_world_ncert_biology_hindi_chunking(self, tokenizer):
        """Validates realistic NCERT Class 10 Hindi Biology text chunking with scientific terminology."""
        chunks = split_text_into_token_chunks(
            self.NCERT_BIOLOGY_HINDI,
            target_tokens=300,
            max_tokens=500,
            tokenizer=tokenizer
        )
        assert len(chunks) >= 2
        for idx, c in enumerate(chunks):
            n_tokens = count_tokens(c, tokenizer)
            assert 50 <= n_tokens <= 500, f"Chunk {idx} token count {n_tokens} outside [50, 500]"
            assert "प्रकाश संश्लेषण" in self.NCERT_BIOLOGY_HINDI

    # =========================================================================
    # 8. REAL-WORLD CODE-MIXED REACT / JAVASCRIPT TUTORIAL
    # =========================================================================

    REACT_HINGLISH_TUTORIAL = """
    React me component-based architecture web applications ko modular aur reusable banata hai.
    Functional components modern React development ka standard pattern hain jisme hooks use kiye jate hain.
    useState hook component ke andar state declare karne ke liye use hota hai:
    ```javascript
    const [counter, setCounter] = useState(0);
    const increment = () => setCounter(prev => prev + 1);
    ```
    useEffect hook side effects handle karne ke liye use hota hai jaise API calls ya DOM manipulation:
    ```javascript
    useEffect(() => {
        fetchUserData(userId).then(data => setUser(data));
        return () => cleanUpSubscription();
    }, [userId]);
    ```
    Props ke through parent component child component ko data pass karta hai unidirectional data flow ke rule par.
    Virtual DOM real DOM ka lightweight in-memory representation hai jo reconciliation algorithm use karke minimum DOM updates karta hai.
    React Context API aur Redux state management complex global states ke prop drilling issue ko solve karte hain.
    Production performance optimization ke liye useMemo aur useCallback hooks unneeded re-renders ko prevent karte hain.
    """ * 4

    def test_real_world_react_hinglish_tutorial_with_code_blocks(self, tokenizer):
        """Verifies code-mixed technical tutorials with embedded code snippets chunk safely <= 500 tokens."""
        chunks = split_text_into_token_chunks(
            self.REACT_HINGLISH_TUTORIAL,
            target_tokens=300,
            max_tokens=500,
            tokenizer=tokenizer
        )
        assert len(chunks) >= 2
        for idx, c in enumerate(chunks):
            n_tokens = count_tokens(c, tokenizer)
            assert n_tokens <= 500, f"React Hinglish chunk {idx} exceeded 500 tokens: {n_tokens}"

    # =========================================================================
    # 9. BOUNDARY: SINGLE-TOKEN, WHITESPACE, AND EMPTY INPUTS
    # =========================================================================

    @pytest.mark.parametrize("empty_input", ["", "   ", "\n\n\n\t\t\n", "   \r\n   "])
    def test_boundary_empty_and_whitespace_inputs(self, tokenizer, empty_input):
        """Empty or whitespace-only inputs return empty chunk list without raising errors."""
        assert split_text_into_token_chunks(empty_input, tokenizer=tokenizer) == []
        assert count_tokens(empty_input, tokenizer) == 0

    @pytest.mark.parametrize("single_word", ["a", "क", "অ", "voltage", "प्रतिरोधकता", "তড়িৎ"])
    def test_boundary_single_word_inputs(self, tokenizer, single_word):
        """Single words produce exactly one valid chunk with correct token count."""
        chunks = split_text_into_token_chunks(single_word, tokenizer=tokenizer)
        assert len(chunks) == 1
        assert chunks[0] == single_word
        assert 1 <= count_tokens(single_word, tokenizer) <= 5

    # =========================================================================
    # 10. BOUNDARY: EMOJIS AND MATHEMATICAL SYMBOLS
    # =========================================================================

    def test_boundary_emojis_and_math_symbols(self, tokenizer):
        """Non-alphanumeric unicode symbols (emojis, math) are handled cleanly without crashing."""
        symbol_text = "⚡️ 🔋 💡 ⚛️ 🔬 📐 🧮 " * 40
        math_text = "∑_{i=1}^n x_i^2 = \\int_0^\\infty f(x) dx \\quad \\forall x \\in \\mathbb{R}. " * 30

        chunks_symbol = split_text_into_token_chunks(symbol_text, tokenizer=tokenizer)
        chunks_math = split_text_into_token_chunks(math_text, tokenizer=tokenizer)

        assert len(chunks_symbol) >= 1
        assert len(chunks_math) >= 1

        for c in chunks_symbol + chunks_math:
            assert count_tokens(c, tokenizer) <= 500

    # =========================================================================
    # 11. BOUNDARY: MASSIVE UNBROKEN TOKEN (No Whitespace)
    # =========================================================================

    def test_boundary_massive_unbroken_token(self, tokenizer):
        """A continuous 800-character unbroken alphanumeric string decomposes safely without crash."""
        massive_token = "विद्युत्चुम्बकीयप्रेरणसिद्धान्तविभवप्रवणताप्रतिरोधकता" * 20
        chunks = split_text_into_token_chunks(massive_token, max_tokens=500, tokenizer=tokenizer)
        assert len(chunks) >= 1
        for c in chunks:
            assert count_tokens(c, tokenizer) <= 500

    # =========================================================================
    # 12. SLIDING-WINDOW OVERLAP VERIFICATION
    # =========================================================================

    def test_sliding_window_overlap_preserves_continuity(self, tokenizer):
        """Verifies that adjacent chunks share overlapping text to maintain context continuity."""
        text = (
            "Sentence one introduces the electric charge concept. "
            "Sentence two explains Coulomb's law between charges. "
            "Sentence three defines the electric field around point charges. "
            "Sentence four explains electric potential as work done. "
            "Sentence five discusses capacitance in electrical circuits. "
            "Sentence six explains dielectric materials in capacitors. "
            "Sentence seven introduces Ohm's law and electrical resistance. "
            "Sentence eight details factors affecting wire resistivity. "
            "Sentence nine explains series and parallel resistor circuits. "
            "Sentence ten summarizes Joule heating and circuit power dissipation. "
        ) * 8

        chunks = split_text_into_token_chunks(
            text,
            target_tokens=150,
            max_tokens=300,
            overlap_pct=0.20,
            tokenizer=tokenizer
        )

        assert len(chunks) >= 3

        # Adjacent chunks should have overlapping sentences
        for i in range(len(chunks) - 1):
            curr_words = set(chunks[i].split())
            next_words = set(chunks[i + 1].split())
            shared_words = curr_words.intersection(next_words)
            assert len(shared_words) >= 5, (
                f"Chunks {i} and {i+1} have zero overlap! Lost semantic continuity."
            )

    # =========================================================================
    # 13. DETERMINISM & STABILITY GUARANTEE
    # =========================================================================

    def test_chunking_determinism(self, tokenizer):
        """Chunking identical text repeatedly must produce exactly identical outputs and counts."""
        sample = self.SANSKRITIZED_HINDI_PHYSICS[:1200]
        run1 = split_text_into_token_chunks(sample, target_tokens=300, max_tokens=500, tokenizer=tokenizer)
        run2 = split_text_into_token_chunks(sample, target_tokens=300, max_tokens=500, tokenizer=tokenizer)
        run3 = split_text_into_token_chunks(sample, target_tokens=300, max_tokens=500, tokenizer=tokenizer)

        assert len(run1) == len(run2) == len(run3)
        for c1, c2, c3 in zip(run1, run2, run3):
            assert c1 == c2 == c3
            assert count_tokens(c1, tokenizer) == count_tokens(c2, tokenizer)

    # =========================================================================
    # 14. TARGET TOKEN BOUND CONVERGENCE
    # =========================================================================

    def test_chunks_converge_near_target_tokens(self, tokenizer):
        """Emitted chunks should average close to target_tokens (300) without collapsing to trivial fragments."""
        sample = self.HINGLISH_CS_TEXT * 2
        chunks = split_text_into_token_chunks(sample, target_tokens=300, max_tokens=500, tokenizer=tokenizer)
        assert len(chunks) >= 3

        # The non-final chunks should be between 200 and 500 tokens
        for c in chunks[:-1]:
            n_tokens = count_tokens(c, tokenizer)
            assert 180 <= n_tokens <= 500, f"Chunk token count {n_tokens} diverged too far from target 300"

