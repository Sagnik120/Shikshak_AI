"""Main RAG service orchestrating document ingestion, embedding, indexing, and retrieval.

Production optimizations:
- TTL-based retrieval result cache (instant cache hits, 5-min expiry)
- PerfTrace instrumentation for end-to-end latency measurement
"""

from __future__ import annotations

import time
import hashlib
import logging
from typing import Optional, List, Dict, Tuple

from modules.rag.src.models import (
    ParsedDocument,
    RetrievalResult,
    GroundedContext,
    Chunk
)
from modules.rag.src.parsing.parser import parse_document
from modules.rag.src.embedding.base import BaseEmbeddingAdapter
from modules.rag.src.embedding.factory import get_embedding_adapter
from modules.rag.src.indexing.vector_store_adapter import VectorStoreAdapter
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.retrieval.retriever import HybridRetriever
from modules.rag.src.grounding.prompt import format_grounding_context_block
from modules.rag.src.perf import begin_trace, end_trace, TimedBlock
from modules.rag.src.retrieval.query_preprocessor import extract_key_query_terms
from modules.mlops.src.agent_trace import (
    RETRIEVAL_ATTEMPT,
    RETRIEVAL_RESOLVED,
    tracer,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL-based retrieval result cache
# ---------------------------------------------------------------------------
_RETRIEVAL_CACHE_TTL_SECONDS = 300  # 5 minutes
_RETRIEVAL_CACHE_MAX_ENTRIES = 512


class _RetrievalCache:
    """Simple TTL-based cache for retrieval results. Thread-safe for single-writer."""

    def __init__(self, max_entries: int = _RETRIEVAL_CACHE_MAX_ENTRIES, ttl: float = _RETRIEVAL_CACHE_TTL_SECONDS):
        self._cache: Dict[str, Tuple[float, RetrievalResult]] = {}
        self._order: List[str] = []
        self._max_entries = max_entries
        self._ttl = ttl

    @staticmethod
    def _make_key(doc_id: str, query: str, top_k: int) -> str:
        raw = f"{doc_id}|{query.strip().lower()}|{top_k}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, doc_id: str, query: str, top_k: int) -> Optional[RetrievalResult]:
        key = self._make_key(doc_id, query, top_k)
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, result = entry
        if (time.time() - ts) > self._ttl:
            # Expired — evict
            self._cache.pop(key, None)
            if key in self._order:
                self._order.remove(key)
            return None
        return result

    def put(self, doc_id: str, query: str, top_k: int, result: RetrievalResult) -> None:
        key = self._make_key(doc_id, query, top_k)
        # Evict oldest if at capacity
        while len(self._order) >= self._max_entries:
            oldest = self._order.pop(0)
            self._cache.pop(oldest, None)
        self._cache[key] = (time.time(), result)
        if key not in self._order:
            self._order.append(key)

    def invalidate(self, doc_id: Optional[str] = None) -> None:
        """Invalidate cache entries. If doc_id given, only invalidate that document's entries."""
        if doc_id is None:
            self._cache.clear()
            self._order.clear()
        else:
            prefix = doc_id
            keys_to_remove = [k for k, (_, r) in self._cache.items() if r.document_id == prefix]
            for k in keys_to_remove:
                self._cache.pop(k, None)
                if k in self._order:
                    self._order.remove(k)


class RAGService:
    """Unified service facade for the Shikshak AI RAG module.

    Production-optimized with TTL-based retrieval caching and PerfTrace instrumentation.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStoreAdapter] = None,
        embedding_adapter: Optional[BaseEmbeddingAdapter] = None
    ):
        self.vector_store = vector_store or ChromaVectorStoreAdapter()
        self.embedding_adapter = embedding_adapter or get_embedding_adapter()
        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            embedding_adapter=self.embedding_adapter
        )
        self._retrieval_cache = _RetrievalCache()
        # Logged once, not per query, so a degraded deploy is obvious without
        # drowning the log.
        self._degraded_warning_logged = False

    def ingest_document(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str = "",
        document_id: Optional[str] = None
    ) -> ParsedDocument:
        """Ingest raw document bytes, parse, chunk, embed, index, and return ParsedDocument (Contract §4).

        Args:
            file_bytes: Raw bytes from UploadRequest.
            filename: Name of the uploaded file.
            mime_type: MIME type string.
            document_id: Optional UUID.

        Returns:
            ParsedDocument strictly matching instructions/Contract.md §4.
        """
        trace = begin_trace()

        # 1. Parse and chunk
        with TimedBlock("parse_and_chunk"):
            parsed_doc = parse_document(
                file_bytes=file_bytes,
                filename=filename,
                mime_type=mime_type,
                document_id=document_id
            )

        # 2. Embed chunks if chunks exist
        if parsed_doc.chunks:
            with TimedBlock("embed_passages"):
                chunk_texts = [c.text for c in parsed_doc.chunks]
                dense_vectors, sparse_weights = self.embedding_adapter.embed_passages(chunk_texts)

            # 3. Upsert into vector store
            with TimedBlock("vector_upsert"):
                embedding_refs = self.vector_store.upsert(
                    document_id=parsed_doc.document_id,
                    chunks=parsed_doc.chunks,
                    dense_embeddings=dense_vectors,
                    sparse_weights=sparse_weights
                )

            # Ensure embedding_ref is populated on all chunks
            for chunk, ref in zip(parsed_doc.chunks, embedding_refs):
                chunk.embedding_ref = ref

        # Invalidate retrieval cache for this document (new content indexed)
        self._retrieval_cache.invalidate(parsed_doc.document_id)

        perf = end_trace()
        if perf:
            logger.info(f"Ingest perf: {perf}")

        return parsed_doc

    def retrieve_context(
        self,
        document_id: Optional[str] = None,
        query_text: str = "",
        top_k: int = 5,
        relevance_threshold: float = 0.5001,
        confidence_threshold: float = 0.52
    ) -> RetrievalResult:
        """Retrieve top grounded chunks for a teaching concept or student question.
        
        If document_id is None or empty, short-circuits to general-knowledge topic-only mode.
        Uses TTL-based cache for repeat queries.
        """
        clean_doc_id = document_id.strip() if document_id and isinstance(document_id, str) else None
        if not clean_doc_id:
            logger.info("retrieve_context called without document_id; short-circuiting to topic-only mode.")
            return RetrievalResult(
                document_id=None,
                query_text=query_text,
                chunks=[],
                has_sufficient_context=False,
                risk_level="no_document_context"
            )

        # Check TTL cache first
        cached = self._retrieval_cache.get(clean_doc_id, query_text, top_k)
        if cached is not None:
            logger.debug(f"Retrieval cache HIT for query: {query_text[:40]}...")
            return cached

        trace = begin_trace()

        result = self.retriever.retrieve(
            document_id=clean_doc_id,
            query_text=query_text,
            top_k=top_k,
            relevance_threshold=relevance_threshold,
            confidence_threshold=confidence_threshold
        )

        perf = end_trace()
        if perf:
            logger.info(f"Retrieve perf: {perf}")

        result = self._guard_degraded_embeddings(result)

        # Cache the result
        self._retrieval_cache.put(clean_doc_id, query_text, top_k, result)

        return result

    def _guard_degraded_embeddings(self, result: RetrievalResult) -> RetrievalResult:
        """Never present hash-fallback retrieval as grounding.

        If the embedding model could not be loaded, the adapter returns
        deterministic hash vectors. Similarity over those is meaningless, but the
        scores still look like scores, so the pipeline would happily report
        `has_sufficient_context=True` and the classroom would cite a learner's
        document for content it never matched. Downgrade to the existing
        high-risk state instead, which callers already handle by teaching from
        general knowledge and showing no citation.
        """
        adapter = getattr(self, "embedding_adapter", None)
        if adapter is None or not getattr(adapter, "is_degraded", False):
            return result

        if not self._degraded_warning_logged:
            logger.error(
                "Embedding model unavailable — retrieval is running on hash fallback vectors. "
                "Document grounding is disabled until the model loads; lessons will teach from "
                "general knowledge instead of citing uploaded material."
            )
            self._degraded_warning_logged = True

        return result.model_copy(
            update={
                "chunks": [],
                "has_sufficient_context": False,
                "risk_level": "high_hallucination_risk",
            }
        )

    # A refinement costs one more embedding+rerank pass, so the loop is capped
    # hard rather than left to a model's judgement.
    MAX_REFINEMENTS = 1

    # Lesson-plan framing words. These are not grammatical stopwords (so they are
    # kept out of the shared preprocessor used by normal retrieval), but in a
    # concept title like "Introduction to the Cell" they carry no document
    # signal and dilute an already-weak short query.
    _FRAMING_WORDS = frozenset(
        {
            "introduction", "intro", "overview", "basics", "basic", "fundamental",
            "fundamentals", "understanding", "understand", "concept", "concepts",
            "key", "core", "advanced", "part", "chapter", "lesson", "topic",
            "summary", "recap", "example", "examples",
        }
    )

    def retrieve_context_agentic(
        self,
        document_id: Optional[str] = None,
        query_text: str = "",
        top_k: int = 5,
        relevance_threshold: float = 0.5001,
        confidence_threshold: float = 0.52,
        topic: Optional[str] = None,
        max_refinements: Optional[int] = None,
        session_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> RetrievalResult:
        """Retrieve, and if the result is not grounded enough, refine once and retry.

        Sufficiency is not a new judgement: it reuses the retriever's existing
        `has_sufficient_context` (top rerank score vs. the 0.52 citation
        threshold). Refinement is deterministic — content terms from the concept
        plus the lesson topic — so the loop adds no LLM call, no quota use and
        stays testable offline.

        The first pass is always kept as the fallback: if refinement does not
        actually improve sufficiency, the original single-pass result is
        returned, so this can only ever match or beat previous behaviour.
        """
        cap = self.MAX_REFINEMENTS if max_refinements is None else max(0, int(max_refinements))

        first = self.retrieve_context(
            document_id=document_id,
            query_text=query_text,
            top_k=top_k,
            relevance_threshold=relevance_threshold,
            confidence_threshold=confidence_threshold,
        )
        self._trace_attempt(session_id, node_id, 1, query_text, first)

        # Topic-only mode has no document to search, and an already-grounded
        # result has nothing to improve. Both stop here, unchanged.
        if first.risk_level == "no_document_context" or first.has_sufficient_context or cap == 0:
            self._trace_resolved(session_id, node_id, first, refined=False)
            return first

        best = first
        attempts = 1
        query = query_text

        while attempts <= cap:
            refined = self._refine_query(query, topic)
            attempts += 1
            if not refined or refined == query:
                break  # nothing new to ask; keep the deterministic first pass

            retry = self.retrieve_context(
                document_id=document_id,
                query_text=refined,
                top_k=top_k,
                relevance_threshold=relevance_threshold,
                confidence_threshold=confidence_threshold,
            )
            self._trace_attempt(session_id, node_id, attempts, refined, retry)
            query = refined

            if retry.has_sufficient_context:
                # model_copy keeps the original query_text visible while
                # recording which refinement actually grounded the node.
                best = retry.model_copy(
                    update={"attempts": attempts, "refined_query": refined, "query_text": query_text}
                )
                break

        if best is first:
            best = first.model_copy(update={"attempts": attempts})

        self._trace_resolved(session_id, node_id, best, refined=best.refined_query is not None)
        return best

    def _refine_query(self, query: str, topic: Optional[str]) -> str:
        """Broaden a weak query deterministically: content terms + lesson topic.

        A node concept like "Introduction to the Cell and Cell Membrane" carries
        framing words that dilute a short dense query; dropping them and adding
        the lesson topic targets the document's own vocabulary instead.
        """
        terms: list[str] = []
        for term in extract_key_query_terms(query or "") + extract_key_query_terms(topic or ""):
            if term in self._FRAMING_WORDS or term in terms:
                continue
            terms.append(term)

        # If framing words were all it had, fall back to the plain content terms
        # rather than returning an empty query.
        if not terms:
            terms = list(dict.fromkeys(extract_key_query_terms(query or "")))
        return " ".join(terms[:12]).strip()

    def _trace_attempt(
        self,
        session_id: Optional[str],
        node_id: Optional[str],
        attempt: int,
        query: str,
        result: RetrievalResult,
    ) -> None:
        tracer.emit(
            RETRIEVAL_ATTEMPT,
            session_id,
            node_id=node_id,
            attempt=attempt,
            query_terms=extract_key_query_terms(query)[:12],
            chunk_count=len(result.chunks),
            top_score=round(float(result.chunks[0].score), 4) if result.chunks else None,
            has_sufficient_context=result.has_sufficient_context,
            risk_level=result.risk_level,
        )

    def _trace_resolved(
        self,
        session_id: Optional[str],
        node_id: Optional[str],
        result: RetrievalResult,
        refined: bool,
    ) -> None:
        tracer.emit(
            RETRIEVAL_RESOLVED,
            session_id,
            node_id=node_id,
            attempts=result.attempts,
            was_refined=refined,
            chunk_count=len(result.chunks),
            has_sufficient_context=result.has_sufficient_context,
            risk_level=result.risk_level,
        )

    def get_grounded_prompt(
        self,
        document_id: Optional[str] = None,
        query_text: str = "",
        top_k: int = 5,
        relevance_threshold: float = 0.5001,
        confidence_threshold: float = 0.52
    ) -> GroundedContext:
        """Convenience method returning ready-to-inject grounding prompt block with chunk IDs."""
        result = self.retrieve_context(
            document_id=document_id,
            query_text=query_text,
            top_k=top_k,
            relevance_threshold=relevance_threshold,
            confidence_threshold=confidence_threshold
        )
        return format_grounding_context_block(
            retrieved_chunks=result.chunks,
            has_sufficient_context=result.has_sufficient_context,
            risk_level=result.risk_level
        )

