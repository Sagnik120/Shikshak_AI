# overview.md — RAG Module (Shikshak AI)

## What This Module Does
The **`rag`** module is the factual grounding, document ingestion, and syllabus research engine of Shikshak AI. It guarantees that the AI Teacher teaches strictly from uploaded learning materials (or verified curriculum knowledge in topic-only mode) without hallucinating facts:
- **Document Ingestion**: Parses `.pdf`, `.docx`, `.pptx`, `.txt`, and `.md` preserving page numbers, slide titles, tables, and heading hierarchies.
- **Multilingual Structure Extraction**: Detects Hindi (`अध्याय`), Bengali (`অধ্যায়`), and Latin chapters, normalizes native Indic numerals (`০-৯`, `०-९`), and extracts TF-IDF key terms with multilingual stopword filtering.
- **Indic Subword-Aware Chunking**: Uses script-aware subword budgeting ($2.4\times$ Indic, $1.3\times$ Latin) ensuring chunks never split across headings and strictly stay $\le 500$ tokens.
- **Hybrid Retrieval & RRF**: Combines BGE-M3 dense semantic vectors (1024-dim) and sparse lexical weights via Reciprocal Rank Fusion ($k=60$).
- **Calibrated Cross-Encoder Reranking**: Re-evaluates candidate chunks with `BAAI/bge-reranker-v2-m3` using calibrated baseline ($0.5001$) and confidence ($0.52$) thresholds.
- **Strict Grounding & Citation Auditing**: Generates prompt context with citation anchors (`[chunk_a1b2]`) and audits generated teacher scripts (`grounded_on: [...]`) for hallucinated references.
- **Topic-Only Teaching Mode**: $O(1)$ fast bypass for `document_id=None` commanding the teacher to use verified pedagogical knowledge and forbidding fake citations.

## Production Engine: Real RAG vs. Mock Policy
- **Actual Production RAG Active**: The RAG module runs **genuine neural models and real vector storage**:
  - **Dense Embeddings**: `BAAI/bge-m3` (1024-dimensional semantic vectors) loaded via `sentence_transformers.SentenceTransformer` (or `FlagEmbedding.BGEM3FlagModel`).
  - **Lexical Matching**: Native token-level sparse weight scoring combined with dense cosine similarity.
  - **Cross-Encoder Reranker**: `BAAI/bge-reranker-v2-m3` loaded via `sentence_transformers.CrossEncoder` performing token-level joint attention over query-candidate pairs.
  - **Vector Database**: Real `chromadb.PersistentClient` (or `EphemeralClient`) constructing an HNSW cosine space index (`hnsw:space: cosine`).
  - **Document Parsers**: Real `pypdf.PdfReader` reading binary streams, `python-docx` traversing XML structures/tables, and `python-pptx` extracting slides/notes.
- **Defensive Mock Fallback Policy**: The codebase contains deterministic fallback blocks (`_model = "mock"`) strictly inside `try...except` exception handlers. This ensures headless CI/CD runner pipelines without GPU or Internet access do not crash automated unit tests. During standard execution and production deployment, real model weights are loaded and active.

## Isolated Web Testbed & Structured Logging (Port 8002)
- **Isolated Server**: Runs independently on **Port 8002** via [`tests/web_test/server.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/tests/web_test/server.py). Production backend (`modules/backend/src/` on port 8000) is never touched.
- **Light Professional Theme**: Strictly utilizes a crisp, clean light theme (no dark mode) featuring Inter typography, slate/blue accents, and intuitive diagnostic panes.
- **Structured Hallucination Logging**: Employs [`tests/web_test/logger.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/tests/web_test/logger.py) writing categorized JSON manifests and formatted text logs into `tests/web_test/logs/` across 7 subdirectories (`parsing/`, `chunking/`, `embedding/`, `indexing/`, `retrieval/`, `grounding/`, `errors/`), tracing the exact `.py` file and function responsible for any hallucination.

## Authoritative Documentation & Reading Sequence
1. [`docs/rag_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/docs/rag_detail.md): Authoritative architectural and file-by-file specification covering all 21 Python files and their Rule-Based vs Dynamic classifications.
2. [`instructions/detail_plan.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/instructions/detail_plan.md): Milestone 1 completed features, Milestone 2 isolated testing/logging, and Real RAG vs Mock architecture.
3. [`instructions/contract.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/instructions/contract.md): Contract §4, Contract §14, internal domain models, and testbed endpoint schemas.
4. [`instructions/detailed_design.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/instructions/detailed_design.md): Deep-dive academic references, model execution hierarchy, and grounding audit architecture.
5. Root [`instructions/Contract.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/instructions/Contract.md): Root system contracts.
