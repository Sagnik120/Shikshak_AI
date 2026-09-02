# 06_Memory.md — Living Memory Log (append-only)

> Format per entry:
> ```
> ### [Phase X] <short title> — <date>
> - Status: <NOT STARTED | IN PROGRESS | STABLE | BLOCKED>
> - Built: ...
> - Tested: ...
> - Stubbed/remaining: ...
> - Deviations/notes: ...
> - Next immediate step: ...
> ```

### [Phase 0] Repo bootstrap — 2026-09-02
- Status: STABLE
- Built: Scaffolded folder structure, gitignore, and cross-module contracts.
- Tested: Directory structure verified.
- Stubbed/remaining: Inter-module endpoints.
- Deviations/notes: none.
- Next immediate step: Phase 1 Ingestion.

### [Phase 1] RAG Ingestion & Document Parsers — 2026-09-02
- Status: STABLE
- Built: Contract §4 ParsedDocument models, multi-format parsers (PDF with OCR fallback, DOCX, PPTX, TXT/MD), TF-IDF key terms and language detector, structure-aware semantic chunker (300/500 tokens, 15% overlap), BGE-M3 & Multilingual E5 embedding adapters, ChromaDB VectorStoreAdapter (Contract §14), hybrid RRF retriever + cross-encoder reranker, grounding prompt generator, and citation extractor.
- Tested: Unit tests for contract schemas, multi-format parsers, edge cases (1-paragraph doc, un-structured doc, 301-token boundary), and eval tests for RRF fusion, relevance floors, and hallucination risk signaling in `modules/rag/tests/`.
- Stubbed/remaining: Live API gateway endpoint connections to `backend`.
- Deviations/notes: Implemented proposed internal extension types (`RetrievalRequest`, `RetrievalResult`, `GroundedContext`) per `detailed_design.md` §9 without modifying shared root `Contract.md`.
- Next immediate step: Connect `backend` ingestion endpoint to `RAGService.ingest_document()`.

