# contract.md — RAG Module (Contract & Schemas)

> **Module Identifier**: `rag`  
> **Repository Path**: `modules/rag/`  
> **Source Code**: [`modules/rag/src/models.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/src/models.py)

---

## 1. Cross-Module Contracts (ROOT `instructions/Contract.md`)

### Contract §4: ParsedDocument & Subtypes
Consumed by `ai_agent_orchestration` (Planner, Explainer) and emitted by `RAGService.ingest_document()`.

```python
class Chunk(BaseModel):
    chunk_id: str                      # Unique ID: chunk_{doc_id[:8]}_{counter:04d}
    text: str                          # Chunk raw text (< 500 tokens)
    section_title: Optional[str] = None # Detected heading/slide title
    page_or_slide: Optional[int] = None # 1-indexed page or slide number
    embedding_ref: str = ""            # Pointer in ChromaDB ({doc_id}#{chunk_id})

class DetectedStructure(BaseModel):
    chapters: List[str] = []           # Chapter/section outline strings
    key_terms: List[str] = []          # Top extracted key phrases (TF-IDF)

class ParsedDocument(BaseModel):
    document_id: str                   # UUID string
    source_lang: str                   # ISO-639-1 code (e.g. 'en', 'hi', 'bn')
    chunks: List[Chunk] = []           # Structured token-bounded chunks
    detected_structure: DetectedStructure = Field(default_factory=DetectedStructure)
    warnings: List[str] = Field(       # Internal diagnostic warnings (excluded from serialization)
        default_factory=list,
        exclude=True
    )
```

### Contract §14: VectorStoreAdapter
Abstract interface implemented by [`ChromaVectorStoreAdapter`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/src/indexing/chroma_adapter.py):

```python
class VectorStoreAdapter(ABC):
    @abstractmethod
    def upsert(
        self,
        document_id: str,
        chunks: List[Chunk],
        dense_embeddings: List[List[float]],
        sparse_weights: Optional[List[Dict[str, float]]] = None
    ) -> List[str]: ...

    @abstractmethod
    def query_dense(self, document_id: str, query_embedding: List[float], top_k: int = 20) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def query_sparse(self, document_id: str, query_sparse: Dict[str, float], top_k: int = 20) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def query(self, embedding: List[float], top_k: int = 5, document_id: Optional[str] = None) -> List[Dict[str, Any]]: ...
```

---

## 2. Internal Domain Types (`modules/rag/src/models.py`)

Used internally and exposed for orchestration consumption:

```python
class RawSection(BaseModel):
    """Internal pre-chunking section extracted from parser."""
    section_title: Optional[str] = None
    page_or_slide: Optional[int] = None
    raw_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RetrievedChunk(BaseModel):
    """Enriched candidate chunk returned by retrieval pipeline."""
    chunk_id: str
    text: str
    section_title: Optional[str] = None
    page_or_slide: Optional[int] = None
    score: float                       # Fused score (RRF or cross-encoder reranker score)
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None

class RetrievalRequest(BaseModel):
    """Query parameters for grounding retrieval."""
    document_id: Optional[str] = None  # None for topic-only teaching mode
    query_text: str
    top_k: int = 5
    relevance_threshold: float = 0.5001

class RetrievalResult(BaseModel):
    """Payload emitted by HybridRetriever and RAGService.retrieve_context()."""
    document_id: Optional[str] = None
    query_text: str
    chunks: List[RetrievedChunk] = []
    has_sufficient_context: bool = True
    risk_level: str = "low"            # 'low', 'moderate_relevance', 'no_document_context', 'high_hallucination_risk'

class GroundedContext(BaseModel):
    """Injection-ready context block for AI Teacher agents."""
    formatted_prompt_context: str
    candidate_chunk_ids: List[str]
    has_sufficient_context: bool
    risk_flag: Optional[str] = None
```

---

## 3. Strict Contract Invariants

1. **Pure Contract §4 Compatibility**: `warnings: List[str]` on `ParsedDocument` is marked `exclude=True`. Serializing `parsed_doc.model_dump()` or `parsed_doc.model_dump_json()` emits strictly the fields specified in ROOT Contract §4.
2. **Topic-Only Nullability**: `RetrievalRequest.document_id`, `RetrievalResult.document_id`, and `RAGService.retrieve_context(document_id=None)` must accept `None` without crashing or querying ChromaDB for empty IDs.
3. **Chunk Token Limits**: Every `Chunk.text` must satisfy $\le 500$ tokens even under complex Indic script expansion.
4. **Citation Tag Syntax**: AI Teacher prompt citations must match `grounded_on: [<chunk_id>, ...]`. Outputting `grounded_on: []` indicates general-knowledge fallback.

---

## 4. Model Execution Contract (Real Neural Models vs. Defensive Fallbacks)

| Component | Production Engine Required | Defensive Offline Fallback (CI Only) | Fallback Trigger |
| :--- | :--- | :--- | :--- |
| **Embedding Adapter** | `sentence_transformers.SentenceTransformer("BAAI/bge-m3")` or `FlagEmbedding.BGEM3FlagModel` (1024-dim dense + lexical sparse) | Deterministic mock hash vectors (128-dim) | Network timeout or missing local HuggingFace weights in offline CI containers |
| **Reranker** | `sentence_transformers.CrossEncoder("BAAI/bge-reranker-v2-m3")` or `FlagEmbedding.FlagReranker` | Normalized lexical word-overlap scoring | Missing transformers or PyTorch execution runtime |
| **Vector Store** | `chromadb.PersistentClient` (Production) or `chromadb.EphemeralClient` (In-Memory) | In-memory dictionary index | ChromaDB installation error |

**Contract Invariant**: In all production and live testing environments, real neural models are loaded. Mock fallbacks are strictly confined to `try...except` rescue blocks and must log warnings if triggered.

---

## 5. Isolated Web Testbed API Contract (`tests/web_test/server.py` on Port 8002)

| Endpoint | Method | Input Schema | Output Schema | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `/api/test/status` | `GET` | None | `{status: "ready", models: {...}, storage: {...}}` | Health and model load verification |
| `/api/test/ingest` | `POST` | `multipart/form-data` or JSON payload | `{document_id, source_lang, chunks_count, detected_structure}` | Full document parsing and indexing |
| `/api/test/chunk` | `POST` | `{text, section_title, target_tokens, max_tokens}` | `{chunk_count, chunks: [...]}` | Semantic chunking inspection |
| `/api/test/embed` | `POST` | `{texts: ["..."]}` | `{dense_dimensions, dense_preview, sparse_keys}` | Embedding inspection |
| `/api/test/retrieve` | `POST` | `{document_id, query_text, top_k, relevance_threshold}` | `RetrievalResult` (Contract §2) | Hybrid retrieval and cross-encoder scores |
| `/api/test/grounding` | `POST` | `{document_id, query_text, simulated_teacher_response}` | `{audit_status, cited_chunk_ids, hallucinated_ids, log_file}` | Prompt block generation & citation audit |
| `/api/test/logs` | `GET` | Optional query `category` | `{total_logs, logs: [...]}` | Manifest list of all category test runs |
| `/api/test/logs/{category}/{filename}` | `GET` | Path params | JSON payload or text log content | Exact file/function audit inspection |

