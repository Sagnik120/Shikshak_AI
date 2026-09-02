"""Main RAG service orchestrating document ingestion, embedding, indexing, and retrieval."""

from __future__ import annotations

import logging
from typing import Optional, List

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

logger = logging.getLogger(__name__)


class RAGService:
    """Unified service facade for the Shikshak AI RAG module."""

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
        # 1. Parse and chunk
        parsed_doc = parse_document(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
            document_id=document_id
        )

        # 2. Embed chunks if chunks exist
        if parsed_doc.chunks:
            chunk_texts = [c.text for c in parsed_doc.chunks]
            dense_vectors, sparse_weights = self.embedding_adapter.embed_passages(chunk_texts)

            # 3. Upsert into vector store
            embedding_refs = self.vector_store.upsert(
                document_id=parsed_doc.document_id,
                chunks=parsed_doc.chunks,
                dense_embeddings=dense_vectors,
                sparse_weights=sparse_weights
            )

            # Ensure embedding_ref is populated on all chunks
            for chunk, ref in zip(parsed_doc.chunks, embedding_refs):
                chunk.embedding_ref = ref

        return parsed_doc

    def retrieve_context(
        self,
        document_id: str,
        query_text: str,
        top_k: int = 5,
        relevance_threshold: float = 0.2
    ) -> RetrievalResult:
        """Retrieve top grounded chunks for a teaching concept or student question."""
        return self.retriever.retrieve(
            document_id=document_id,
            query_text=query_text,
            top_k=top_k,
            relevance_threshold=relevance_threshold
        )

    def get_grounded_prompt(
        self,
        document_id: str,
        query_text: str,
        top_k: int = 5
    ) -> GroundedContext:
        """Convenience method returning ready-to-inject grounding prompt block with chunk IDs."""
        result = self.retrieve_context(document_id, query_text, top_k=top_k)
        return format_grounding_context_block(
            retrieved_chunks=result.chunks,
            has_sufficient_context=result.has_sufficient_context,
            risk_level=result.risk_level
        )
