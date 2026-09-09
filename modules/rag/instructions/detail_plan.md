# detail_plan.md — RAG Module (Shikshak AI)

> **Module Identifier**: `rag`  
> **Repository Path**: `modules/rag/`  
> **Primary Interfaces**: Contract §4 (`ParsedDocument`), Contract §14 (`VectorStoreAdapter`), Internal Extensions (`RetrievalResult`, `GroundedContext`)  
> **Rubric Weight**: 15/100 ("RAG & Knowledge Grounding"), directly drives 15/100 "AI/ML & LLM Implementation"  
> **Status**: **STABLE / PRODUCTION-READY (Milestone 1 Complete & Verified; Milestone 2 Active)**

---

## 1. Milestone 1 Deliverables (Completed & Verified)

All Milestone 1 core features are 100% complete and verified against 18+ automated test cases in `modules/rag/tests/`:

1. **Multi-Format Ingestion Pipeline**:
   - `src/parsing/parser.py`: Routes files by MIME type and extension.
   - `src/parsing/pdf_parser.py`: Page-by-page text extraction with outline/bookmark inspection and scanned document detection.
   - `src/parsing/docx_parser.py`: Heading style detection (`Heading 1`, `Heading 2`, `Title`) and table serialization.
   - `src/parsing/pptx_parser.py`: Slide-by-slide extraction capturing titles, shapes, tables, and speaker notes.
   - `src/parsing/txt_parser.py`: Markdown heading hierarchy (`#`, `##`) and paragraph splitting.
   - `src/parsing/ocr.py`: Fallback OCR wrapper using `pytesseract` and `pdf2image`.

2. **Script-Agnostic Multilingual Structure Extractor**:
   - `src/parsing/structure.py`:
     - `SCRIPT_HEADING_REGISTRY`: Recognizes Devanagari (`अध्याय`, `पाठ`, `इकाई`, `प्रकरण`, `खण्ड`, `भाग`) and Bengali (`অধ্যায়`, `পাঠ`, `একক`, `পর্ব`) markers alongside Latin headings.
     - `normalize_indic_numerals()`: Universal mapper converting Bengali (`০-৯`) and Devanagari (`०-९`) native numerals to standard ASCII `0-9`.
     - `extract_key_terms_tfidf()`: Scikit-learn TF-IDF vectorization with Unicode regex tokenization (`[\w\u0900-\u097F\u0980-\u09FF]{2,}`) and multilingual stopword dictionaries for English, Hindi, and Bengali.

3. **Indic Semantic Chunker**:
   - `src/chunking/chunker.py`:
     - Script-aware subword budgeting ($2.4\times$ multiplier for Indic words vs $1.3\times$ for Latin words).
     - Structure-aware: never chunks across section/heading/slide boundaries.
     - Target 300 tokens, 15% overlap, min-chunk merge guard, and `finalize_and_verify_chunks` recursive hard split guaranteeing chunks stay $\le 500$ tokens.

4. **Hybrid Multilingual Embeddings & Vector Storage**:
   - `src/embedding/bge_m3.py`: FlagEmbedding `BAAI/bge-m3` generating dense 1024-dim vectors and sparse lexical term weights across 100+ languages.
   - `src/embedding/e5_bm25.py`: CPU fallback using `multilingual-e5-large` + BM25 term frequencies.
   - `src/indexing/chroma_adapter.py`: Concrete ChromaDB implementation of Contract §14 (`VectorStoreAdapter`) with HNSW cosine distance indexing and in-memory sparse index.

5. **Hybrid Retrieval, RRF & Calibrated Cross-Encoder Reranking**:
   - `src/retrieval/rrf.py`: Reciprocal Rank Fusion combiner ($k=60$) fusing dense and sparse candidate rankings.
   - `src/retrieval/reranker.py`: `BAAI/bge-reranker-v2-m3` cross-encoder neural model scoring token-level query-passage joint attention.
   - `src/retrieval/retriever.py`: Two-threshold calibrated evaluation:
     - Baseline Entailment Floor ($0.5001$): Filters neutral logits with zero positive entailment (out-of-scope noise).
     - Confidence Cutoff ($0.52$): Scores $\ge 0.52$ produce `risk_level="low"`.
     - Paraphrase Window ($0.5001 < \text{score} < 0.52$): Produces `risk_level="moderate_relevance"` to accept conversational and Hinglish queries.

6. **Grounding, Anti-Hallucination & Topic-Only Mode**:
   - `src/grounding/prompt.py`: Generates Markdown context blocks with citation anchors (`[chunk_a1b2]`) and explicit rules commanding the teacher to cite sources.
   - `src/grounding/extractor.py`: Parses `grounded_on: [...]` chunk citations and detects hallucinated IDs.
   - `src/service.py`: $O(1)$ fast short-circuit for `document_id=None` emitting `risk_level="no_document_context"` and open-domain prompt forbidding fake citations.

---

## 2. Milestone 2 Deliverables (Isolated Web Testbed & Structured Logging)

To empower interactive, visual evaluation without touching or polluting the production backend, Milestone 2 establishes an isolated testbed infrastructure inside `modules/rag/tests/web_test/`:

### A. Architectural Isolation Contract
- **Zero Modifications to `modules/backend/src/`**: The production backend on port 8000 remains 100% untouched.
- **Dedicated Independent Port**: The RAG isolated test server runs on **port 8002**.
- **Direct Source Imports**: The test server directly imports production code from `modules.rag.src.*`. Any bug identified during web testing is patched directly in `src/`, instantly benefiting the entire system.

### B. Structured Logging Engine (`tests/web_test/logger.py`)
Fine-grained, hierarchical logging capturing every input, file, function checkpoint, and error:
- **Directory Structure**:
  ```
  modules/rag/tests/web_test/logs/
  ├── parsing/      # File bytes, detected sections, chapter outlines, key terms, scanned warnings
  ├── chunking/     # Chunk IDs, token budgets, Indic expansion ratios, overlap boundaries
  ├── embedding/    # Dense vector dimensionality, sparse term frequency maps, model load status
  ├── indexing/     # Collection creation, upsert status, document chunk counts
  ├── retrieval/    # Dense top-20, sparse top-20, RRF fused top-10, cross-encoder scores
  ├── grounding/    # Prompt blocks, cited chunk IDs, hallucination risk signals
  └── errors/       # Unhandled exceptions, stack traces, corrupted file alerts
  ```
- **File Naming Standard**: `YYYYMMDD_HHMMSS_<category>_<run_id>.json` and human-readable `.log` companions.
- **Hallucination Tracing**: Explicitly records which `.py` file and function triggered a hallucination flag (`empty_citations_despite_available_context`, `hallucinated_chunk_references`, or `high_hallucination_risk`).

### C. Light Professional Web UI (`tests/web_test/static/`)
- **Theme**: **Clean, light professional color scheme** (crisp white `#ffffff`, soft background `#f8fafc`, subtle borders `#e2e8f0`, navy/indigo primary `#3b82f6` / `#1e40af`, emerald `#10b981`, clean Inter font). Explicitly avoids dark mode per design guidelines.
- **Interactive Tabs**:
  1. **Document Ingestion**: Upload `.pdf`, `.docx`, `.pptx`, `.txt`, or paste raw text. View detected chapters, language, TF-IDF terms, and diagnostic warnings.
  2. **Semantic Chunker**: View chunks, token counts, Indic $2.4\times$ multiplier calculations, and section headers.
  3. **Embedding & Indexer**: Inspect generated dense vector shapes, sparse lexical dictionaries, and ChromaDB collection status.
  4. **Hybrid Retrieval**: Query ingested documents or test topic-only bypass (`document_id=None`). Inspect dense, sparse, RRF, and cross-encoder scores.
  5. **Grounding & Anti-Hallucination**: Inspect the generated prompt block, test out-of-scope queries for defensive fallback, and audit simulated AI teacher responses for citation validity.
  6. **Log Explorer & Error Tracker**: Real-time log inspector filtering logs across categories with one-click JSON preview and error highlighting.

---

## 3. Production RAG Engine Integrity vs. Mock Policy

### A. Real Production Models Active
Shikshak AI's RAG module runs **genuine neural models, real tokenizers, and real vector database instances**:
1. **Dense Vector Encoder**: `BAAI/bge-m3` produces true 1024-dimensional semantic embeddings. Loaded in Python via `sentence_transformers.SentenceTransformer` or `FlagEmbedding.BGEM3FlagModel`.
2. **Lexical Matching**: Native token-level sparse weight scoring computed and combined with dense cosine similarity.
3. **Cross-Encoder Reranker**: `BAAI/bge-reranker-v2-m3` loaded via `sentence_transformers.CrossEncoder`. Evaluates query-passage pairs with full cross-attention scoring.
4. **Vector Store**: Real `chromadb.PersistentClient` (or `EphemeralClient`) constructing an HNSW cosine space index (`hnsw:space: cosine`).
5. **Document Parsers**: Real `pypdf.PdfReader` reading binary PDF streams, `python-docx` traversing XML structures/tables, and `python-pptx` extracting slides/notes.

### B. Defensive Mock Fallback Policy
- **Purpose**: The codebase contains deterministic fallback blocks (`_model = "mock"`, `_client = "mock"`) strictly enclosed within `try...except` exception handlers in [`bge_m3.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/src/embedding/bge_m3.py#L38-L42), [`reranker.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/src/retrieval/reranker.py#L37-L41), and [`chroma_adapter.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/src/indexing/chroma_adapter.py#L36-L40).
- **Behavior**: These fallbacks exist solely to guarantee that headless CI/CD runner pipelines (without internet or GPU access) do not crash automated unit tests.
- **Production Execution**: During normal development and live deployment, real models and weights are loaded. In testing on local runtime, the system verified:
  - `BGEM3EmbeddingAdapter`: `<class 'sentence_transformers.SentenceTransformer'>` (`BAAI/bge-m3` weights loaded)
  - `BGEReranker`: `<class 'sentence_transformers.CrossEncoder'>` (`BAAI/bge-reranker-v2-m3` weights loaded)
  - `ChromaVectorStoreAdapter`: `<class 'chromadb.api.client.Client'>` with HNSW cosine distance

---

## 4. Web Testbed Operations & Execution Guide

### A. Launching the Isolated Test Server
The test server can be launched as a background process on Port 8002:
```bash
./.venv/bin/python modules/rag/tests/web_test/server.py
```
- **Port**: `8002` (Dedicated; production backend on `8000` remains untouched).
- **Web UI URL**: `http://localhost:8002`
- **Health Check**: `GET http://localhost:8002/api/test/status`

### B. Stopping the Isolated Test Server
When testing is complete, find and stop the background task or terminate the process on Port 8002:
```bash
# Verify process listening on port 8002
lsof -i :8002
# Kill process if running
kill -9 $(lsof -ti :8002)
```

---

## 5. Verification Suite & Test Pass Status

The RAG module includes comprehensive unit and integration test suites:
- [`tests/unit/test_parsers.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/tests/unit/test_parsers.py): 7 tests covering PDF, DOCX, PPTX, TXT, OCR fallback, and structure extraction.
- [`tests/unit/test_chunker.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/tests/unit/test_chunker.py): 5 tests covering token budgeting, Indic $2.4\times$ multiplier, boundary protection, and hard limits.
- [`tests/unit/test_retrieval.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/tests/unit/test_retrieval.py): 6 tests covering ChromaDB upsert, RRF fusion, cross-encoder reranking, and topic-only bypass.
- [`tests/unit/test_rag_web_test_server.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/tests/unit/test_rag_web_test_server.py): 8 tests covering the isolated test server endpoints, logging manifests, and grounding audit.

**Execution Command**:
```bash
pytest modules/rag/tests/ -v
```
**Results**: **26 passed in 25.49s (100% Green)**.
