# overview.md — ml_core

## Mission Statement
The `ml_core` module provides dedicated, lightweight machine learning algorithms, deterministic evaluation rules, and pedagogical diagnostic models for Shikshak AI. It acts as the intelligent grading assistant and pedagogical classifier, replacing slow, expensive, and hallucination-prone raw LLM calls with robust, deterministic heuristics and constrained, rubric-bound judge models.

---

## Core Capabilities
1. **Deterministic MCQ Scoring**: Zero-latency, exact-string answer matching with 0% hallucination risk.
2. **Hybrid Semantic Answer Evaluation**: Two-stage pipeline combining embedding cosine similarity pre-filtering ($\ge 0.88$ pass, $< 0.40$ fail) with a constrained Gemini zero-temperature rubric judge for ambiguous submissions.
3. **Misconception Classification**: Diagnoses the root flaw in incorrect student answers against curated per-subject pedagogical taxonomies (`physics`, `math`, `cs`).
4. **Concept & Key-Term Extraction**: Extracts high-relevance domain entities and keyphrases from lesson text to index lesson graph nodes.
5. **Visual-Type Recommendation**: Heuristic rule table with LLM fallback mapping concepts to optimal visual modalities (`equation`, `graph`, `diagram`, `code`, `timeline`, `map`).
6. **Dedicated Web Testbed Studio**: Standalone FastAPI diagnostic service on **Port 8003** with an elegant, modern light professional UI and hierarchical execution logging.

---

## Directory Map
```
modules/ml_core/
├── docs/
│   └── ml_core_detail.md                  # Comprehensive architectural and technical specification
├── instructions/
│   ├── contract.md                        # Cross-module contract bindings (§9, §10, §5, §6)
│   ├── detail_plan.md                     # Implementation plan, components, and testbed details
│   └── overview.md                        # High-level mission and directory map
├── src/
│   ├── answer_evaluation/                 # MCQ and Freeform hybrid evaluators
│   ├── concept_extraction/                # Key-term and concept extraction engine
│   ├── embeddings/                        # Fast semantic embedding adapters
│   ├── misconception/                     # Misconception classifier and taxonomy stores
│   ├── schemas/                           # Internal data transfer models
│   ├── service.py                         # MLCoreService unified facade
│   └── visual_suggestion/                 # Visual type rule table and recommender
└── tests/
    ├── integration/                       # Boundary tests with orchestrator and RAG
    ├── unit/                              # Pytest test cases (28 passing tests)
    └── web_test/                          # Standalone diagnostic testbed (Port 8003)
        ├── logger.py                      # Hierarchical logging engine
        ├── server.py                      # FastAPI testbed application
        ├── logs/                          # Categorized test trace logs
        └── static/                        # Light professional diagnostic UI
```

---

## Required Readings
1. Root `instructions/Contract.md` (specifically Contract §9 and §10)
2. Root `02_Architecture.md`
3. Module `instructions/detail_plan.md`
4. Module `docs/ml_core_detail.md`
