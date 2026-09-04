# Progress — 2026-09-02T19:12:00+05:30
Overall Status: IN PROGRESS (RAG module Phase 0, 1 & 2 Retrieval STABLE)

## Phases (04_Phases.md)
- [x] Phase 0 — Skeleton (RAG scaffolding, models, and interfaces complete)
- [x] Phase 1 — Adapters & Ingestion (Multi-format parsers PDF/DOCX/PPTX/TXT, OCR fallback, TF-IDF structure, Chroma adapter)
- [x] Phase 2 — Planning & Retrieval (RAG component: BGE-M3 embeddings, hybrid RRF retrieval, BGE cross-encoder reranking, grounding prompt verification — 35/35 tests passing)
- [ ] Phase 3 — Explanation & Visual Selection
- [x] Phase 4 — Video Generation (avatar_voice: Multilingual TTS, Viseme 2D Avatar @ 24 FPS, 6 Subject-Aware Visual Renderers, FFmpeg Compositor, Async Queue)
- [ ] Phase 5 — Interaction Loop
- [ ] Phase 6 — Evaluation & Adaptation
- [ ] Phase 7 — Assessment & Learner Profile
- [ ] Phase 8 — Frontend Polish & Multilingual
- [ ] Phase 9 — Documentation & Demo

## Mandatory Requirements Checklist (PS §17)
- [x] Learning from uploaded material (RAG complete & grounded)
- [ ] Topic-based teaching
- [ ] AI-generated lesson structure
- [ ] Personalized teaching
- [ ] Human-like teaching interaction
- [x] Video-based AI Teacher presentation (1920x1080 canvas, 70% visual viewport, 30% avatar PiP, bottom captions)
- [x] AI voice (Multilingual Edge-TTS Neural + offline waveform fallback)
- [x] Human-like AI avatar (Viseme-driven animated teacher avatar @ 24 FPS with transparent RGBA frames & cue poses)
- [x] Multilingual capability (Multilingual BGE-M3 embeddings, Hindi/English parser, Swara/Madhur/Neerja/Aria neural voices)
- [ ] Student questioning & assessment
- [ ] Adaptive response to student performance
- [ ] Working application/prototype

## Round 2 Review Verification Summary (00_OVERALL_ROUND2_REVIEW.md)
1. **Tier 2 Neural Avatar**: `MuseTalkAvatarAdapter` implemented with hardware acceleration checks, model weights validation, test mode, and transparent fallback (`tests/unit/test_musetalk_tier_reporting.py` — 7/7 passed).
2. **Reranker Threshold Calibration**: Calibrated two-threshold architecture ($0.5001$ baseline vs $0.52$ citation) preserving 100% recall on conversational in-scope paraphrases while strictly rejecting out-of-scope queries (`tests/eval/test_reranker_recall_precision.py` — 27/27 passed).
3. **Subword Token Budgeting**: Script-aware per-word weighting ($2.4\times$ Indic, $1.3\times$ Latin) with trailing fragment merge guard and `finalize_and_verify_chunks` recursive splitter guaranteeing $\le 500$ tokens (`tests/unit/test_chunker_real_token_ground_truth.py` — 23/23 passed).
4. **Multilingual Expansion**: Data-driven `SCRIPT_HEADING_REGISTRY` covering Bengali (`[\u0980-\u09FF]`) and Devanagari (`[\u0900-\u097F]`), universal Indic numeral normalizer (`০-৯` and `०-९` $\rightarrow$ `0-9`), and Bengali TF-IDF stopwords (`tests/unit/test_structure_script_dispatcher.py` — 38/38 passed).
5. **Multi-Domain Faithfulness Benchmark**: Expanded eval suite to Physics, NCERT Class 10 Hindi Biology, and CS Graphs (`tests/eval/test_rag_groundedness.py` — 20/20 passed).
6. **Cross-Platform Preflight Enhancements**: `scripts/preflight_check.py` upgraded with `--require-ffmpeg`, `--check-tier2`, and `--json` machine-readable output (`tests/unit/test_preflight_enhanced.py` — 8/8 passed).

## Known Issues / Blockers
- None. All 35 pytest cases and 12 diagnostic cases pass with 100% success rate.
