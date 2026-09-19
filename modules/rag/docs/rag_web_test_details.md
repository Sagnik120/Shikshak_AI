# RAG Module — Web Test Specification

## 1. Purpose
This document provides the definitive manual test specification for the Shikshak AI RAG (Retrieval-Augmented Generation) module. It defines exactly how a human QA engineer can systematically verify document ingestion, parsing, chunking, embedding, indexing, retrieval, and grounding using the isolated web testbed (`Port 8002`), ensuring production parity.

## 2. Execution Mode & Secrets Safety
**CRITICAL:** The RAG module itself **DOES NOT USE GEMINI** or any external LLM APIs directly.
* All embeddings use LOCAL models (e.g., `BGE-M3`, `E5-BM25`).
* All reranking uses LOCAL models (e.g., `BGEReranker`, `CrossEncoder`).
* All parsing (including OCR via `pytesseract`) is LOCAL.
* **Therefore, NO external API keys or Gemini quotas are consumed during RAG testing.**

All tests in this document are categorized as **LOCAL / DETERMINISTIC**.

## 3. Production vs. Web Test Parity
This testbed directly imports the actual production classes from `modules/rag/src/`.

### Web Test Verifies:
* `parse_document`, `extract_raw_sections` (Parsers)
* `chunk_sections`, `split_text_into_token_chunks` (Chunker)
* `BGEM3EmbeddingAdapter`, `E5BM25EmbeddingAdapter` (Embeddings)
* `ChromaVectorStoreAdapter` (Indexing)
* `HybridRetriever`, `BGEReranker`, `reciprocal_rank_fusion` (Retrieval)
* `format_grounding_context_block`, `parse_grounded_citations` (Grounding utilities)

### Production Pipeline Additionally Requires:
* Backend invocation (FastAPI routes connecting Orchestrator to RAGService).
* Concurrency handling at the backend level.
* Real orchestrator agent invocations (which consume the formatted grounding blocks).

## 4. Test Data Recommendations
Prepare the following small fixtures before testing to avoid bloated indexing times:
1. **Physics Sample (`physics.pdf`)**: 2-3 pages with headings and equations (Newton's Laws).
2. **Hindi Sample (`hindi.docx`)**: 1 page of Hindi text to verify multilingual parsing/chunking.
3. **Empty File (`empty.txt`)**: 0 bytes.
4. **Image-heavy PDF (`scanned.pdf`)**: To verify Tesseract OCR fallback.
5. **Simulated Agent Output (`agent_output.json`)**: Containing a fake citation `[doc_xyz, chunk_abc]`.

---

## 5. Test Matrix: A. Document Ingestion & Parsing
*Location: Web Testbed -> Document Ingestion Tab*

### RAG-ING-01 — Valid PDF Parsing
**Purpose:** Verify PDF extraction and heading detection.
**Input:** `physics.pdf`
**Execution:** Upload file -> Click "Parse Document".
**Expected Output:** Valid `ParsedDocument` JSON. Detected language `en`. Sections array populated with correct heading boundaries.
**PASS if:** Text is successfully extracted without crashing and structure array is not empty.

### RAG-ING-02 — OCR Fallback
**Purpose:** Verify OCR triggers on image-based PDFs.
**Input:** `scanned.pdf`
**Execution:** Upload file -> Parse.
**Expected Output:** Text extracted via Tesseract.
**PASS if:** Returned text matches the scanned image content (minor OCR typos acceptable).

### RAG-ING-03 — Empty Document
**Purpose:** Verify error handling for empty files.
**Input:** `empty.txt`
**Execution:** Upload file -> Parse.
**Expected Output:** Controlled 400/422 HTTP Error or empty sections array.
**PASS if:** System does not crash with a 500 Python traceback.

### RAG-ING-04 — Multilingual DOCX
**Purpose:** Verify Hindi language detection and Word doc parsing.
**Input:** `hindi.docx`
**Execution:** Upload file -> Parse.
**Expected Output:** Language detected as `hi` (or `mr`/`bn` depending on strictness). Text extracted properly without unicode mojibake.

---

## 6. Test Matrix: B/C. Semantic Chunking
*Location: Web Testbed -> Semantic Chunker Tab*

### RAG-CHK-01 — Normal Token Constraints
**Purpose:** Verify chunk boundaries respect max tokens and overlap.
**Input:** `ParsedDocument` output from RAG-ING-01.
**Execution:** Feed sections to Chunker -> Execute.
**Expected Output:** Array of `Chunk` objects.
**PASS if:** Every chunk's `token_count` is ≤ max tokens (e.g., 512). Successive chunks share overlapping text.

### RAG-CHK-02 — Short Content
**Purpose:** Verify single-chunk generation.
**Input:** 1 paragraph of text.
**Execution:** Chunk.
**Expected Output:** Exactly 1 chunk containing the exact text.

---

## 7. Test Matrix: D/E. Embeddings & ChromaDB Indexing
*Location: Web Testbed -> Embeddings & Store Tab*

### RAG-IDX-01 — Valid Document Indexing
**Purpose:** Verify local BGE-M3 embedding and ChromaDB persistence.
**Input:** Chunks from RAG-CHK-01.
**Execution:** Click "Embed & Store".
**Expected Output:** Success message indicating N chunks inserted into ChromaDB.
**PASS if:** No dimension mismatch errors. ChromaDB reports successful insertion.

### RAG-IDX-02 — Duplicate Insertion
**Purpose:** Verify idempotency or graceful handling of duplicates.
**Input:** Same chunks from RAG-IDX-01.
**Execution:** Click "Embed & Store" again.
**Expected Output:** Either silently updates/ignores or creates distinct UUIDs.
**PASS if:** Does not crash the database.

---

## 8. Test Matrix: F/G. Hybrid Retrieval & Reranking
*Location: Web Testbed -> Hybrid Retrieval & RRF Tab*
*(Ensure RAG-IDX-01 is complete before running these)*

### RAG-RET-01 — Exact Keyword Query (In-Scope)
**Purpose:** Verify dense/sparse retrieval finds exact matches.
**Input:** Query: `"Newton's first law"`
**Execution:** Execute Hybrid Retrieval.
**Expected Output:** `RetrievalResult` JSON containing chunks from `physics.pdf`.
**PASS if:** The most relevant chunk is ranked #1.

### RAG-RET-02 — Semantic Query
**Purpose:** Verify dense embeddings capture meaning beyond keywords.
**Input:** Query: `"What happens to an object when no forces push it?"`
**Execution:** Execute Hybrid Retrieval.
**Expected Output:** Chunks discussing inertia/First Law.
**PASS if:** Relevant chunks are retrieved even without matching exact physics terminology.

### RAG-RET-03 — Out-of-Scope Query
**Purpose:** Verify threshold boundaries reject irrelevant documents.
**Input:** Query: `"Explain photosynthesis in plants."`
**Execution:** Execute Retrieval.
**Expected Output:** Empty results `[]` OR very low confidence scores.
**PASS if:** System does not confidently return physics chunks for biology queries.

### RAG-RET-04 — CrossEncoder Reranking
**Purpose:** Verify reranker reorders base retrieval results.
**Input:** Query: `"Force equation"`
**Execution:** Check initial dense rank vs final CrossEncoder rank.
**PASS if:** Reranker scores are populated in the JSON output, proving the local model executed.

---

## 9. Test Matrix: H. Grounding & Anti-Hallucination
*Location: Web Testbed -> Grounding & Hallucination Tab*

### RAG-GRND-01 — Valid Citation Parsing
**Purpose:** Verify orchestrator utilities can extract citations.
**Input:** Text: `"Inertia is a property of matter [doc_123, chunk_456]."`
**Execution:** Execute Citation Parser.
**Expected Output:** Array containing tuple/object linking to `chunk_456`.
**PASS if:** Regex successfully captures the bracketed citation.

### RAG-GRND-02 — Missing Citation
**Purpose:** Verify hallucination detection handling.
**Input:** Text: `"Inertia is a property of matter."`
**Execution:** Execute Citation Parser.
**Expected Output:** Empty array `[]`.

---

## 10. End-to-End Scenarios
*Location: Web Testbed -> Combined workflow across tabs*

### RAG-FULL-01 — Complete Local Pipeline
1. **Upload** `physics.pdf`.
2. **Parse** to get `ParsedDocument`.
3. **Chunk** the sections.
4. **Embed & Index** into ChromaDB.
5. **Retrieve** using query `"inertia"`.
**Verify:** The entire pipeline executes using only local CPU/GPU resources without any 500 errors or network failures.

---

## 11. Pass/Fail Recording Template

Copy and paste this template when conducting QA:

```text
Date: [YYYY-MM-DD]
Tester: [Name]
Environment: [Windows/Local]
Model/version: [BGE-M3 / local chromadb]
Git commit: [Hash]

| Test ID       | Result | Observed Output | Expected Output | Issue Class | Evidence |
|---------------|--------|-----------------|-----------------|-------------|----------|
| RAG-ING-01    |        |                 |                 |             |          |
| RAG-ING-02    |        |                 |                 |             |          |
| RAG-CHK-01    |        |                 |                 |             |          |
| RAG-IDX-01    |        |                 |                 |             |          |
| RAG-RET-01    |        |                 |                 |             |          |
| RAG-RET-03    |        |                 |                 |             |          |
| RAG-FULL-01   |        |                 |                 |             |          |
```

*Issue Classifications:* Implementation Bug, Test Harness Bug, Configuration Issue, Environment Issue, Test Input Issue, Expected Behavior.
