"""Hybrid retrieval pipeline combining dense semantic search, sparse lexical search, RRF fusion, and cross-encoder reranking."""

from __future__ import annotations

import logging
from typing import List, Optional

from modules.rag.src.models import (
    RetrievedChunk,
    RetrievalRequest,
    RetrievalResult
)
from modules.rag.src.embedding.base import BaseEmbeddingAdapter
from modules.rag.src.embedding.factory import get_embedding_adapter
from modules.rag.src.indexing.vector_store_adapter import VectorStoreAdapter
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.retrieval.rrf import reciprocal_rank_fusion
from modules.rag.src.retrieval.reranker import BGEReranker

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Full hybrid retrieval engine (Dense + Sparse + RRF + BGE Rerank)."""

    def __init__(
        self,
        vector_store: Optional[VectorStoreAdapter] = None,
        embedding_adapter: Optional[BaseEmbeddingAdapter] = None,
        reranker: Optional[BGEReranker] = None
    ):
        self.vector_store = vector_store or ChromaVectorStoreAdapter()
        self.embedding_adapter = embedding_adapter or get_embedding_adapter()
        self.reranker = reranker or BGEReranker()

    def retrieve(
        self,
        document_id: str,
        query_text: str,
        top_k: int = 5,
        relevance_threshold: float = 0.5001,
        confidence_threshold: float = 0.52
    ) -> RetrievalResult:
        """Execute hybrid retrieve-then-rerank pipeline per detailed_design.md §5.

        Steps:
        1. Embed query (dense vector + sparse lexical weights).
        2. Retrieve top-20 dense candidates and top-20 sparse candidates from vector store.
        3. Fuse candidate lists using Reciprocal Rank Fusion (RRF) -> top 10.
        4. Cross-encoder rerank top 10 with BAAI/bge-reranker-v2-m3 -> top-k (default 5).
        5. Two-threshold calibrated evaluation:
           - In neural cross-encoder reranking, sigmoid scores <= 0.5001 represent neutral
             logits (0 ± 0.0002) with zero positive entailment (out-of-scope cross-domain queries).
             These are strictly filtered out as cross-domain noise.
           - If top_score >= confidence_threshold (0.52): has_sufficient=True, risk_level="low".
           - If 0.5001 < top_score < confidence_threshold: has_sufficient=True, risk_level="moderate_relevance"
             (successfully accepts conversational paraphrases and Hinglish queries).
           - If top_score <= 0.5001 or not retrieved_chunks: has_sufficient=False, risk_level="high_hallucination_risk".
        """
        import re
        if not query_text.strip() or not re.search(r'\w', query_text):
            return RetrievalResult(
                document_id=document_id,
                query_text=query_text,
                chunks=[],
                has_sufficient_context=False,
                risk_level="high_hallucination_risk"
            )

        # 1. Embed query
        dense_q, sparse_q = self.embedding_adapter.embed_query(query_text)

        # 2. Candidate retrieval (top 20 each)
        dense_candidates = self.vector_store.query_dense(document_id, dense_q, top_k=20)
        sparse_candidates = self.vector_store.query_sparse(document_id, sparse_q, top_k=20)

        if not dense_candidates and not sparse_candidates:
            return RetrievalResult(
                document_id=document_id,
                query_text=query_text,
                chunks=[],
                has_sufficient_context=False,
                risk_level="high_hallucination_risk"
            )

        # 3. RRF Fusion -> top 10
        fused_top10 = reciprocal_rank_fusion(
            ranked_lists=[dense_candidates, sparse_candidates],
            k=60,
            top_n=10
        )

        # 4. Rerank -> top_k
        reranked_top_k = self.reranker.rerank(
            query=query_text,
            candidates=fused_top10,
            top_k=top_k
        )

        # Build RetrievedChunk models
        retrieved_chunks: List[RetrievedChunk] = []
        for item in reranked_top_k:
            retrieved_chunks.append(
                RetrievedChunk(
                    chunk_id=item["chunk_id"],
                    text=item["text"],
                    section_title=item.get("section_title"),
                    page_or_slide=item.get("page_or_slide"),
                    score=item["score"],
                    dense_score=item.get("dense_score"),
                    sparse_score=item.get("sparse_score")
                )
            )

        # 5. Two-threshold calibrated evaluation
        top_score = retrieved_chunks[0].score if retrieved_chunks else 0.0
        top_chunk = retrieved_chunks[0] if retrieved_chunks else None

        is_cross_domain_noise = False
        if top_chunk and top_score <= relevance_threshold:
            is_cross_domain_noise = True

        if is_cross_domain_noise or not retrieved_chunks or top_score < relevance_threshold:
            has_sufficient = False
            risk_level = "high_hallucination_risk"
            retrieved_chunks = []
        elif top_score >= confidence_threshold:
            has_sufficient = True
            risk_level = "low"
        else:
            has_sufficient = True
            risk_level = "moderate_relevance"

        return RetrievalResult(
            document_id=document_id,
            query_text=query_text,
            chunks=retrieved_chunks,
            has_sufficient_context=has_sufficient,
            risk_level=risk_level
        )
