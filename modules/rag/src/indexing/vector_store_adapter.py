"""Vector store adapter interface strictly adhering to ROOT instructions/Contract.md §14."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from modules.rag.src.models import Chunk


class VectorStoreAdapter(ABC):
    """Authoritative vector store interface matching Contract §14:

    VectorStoreAdapter.upsert(chunks) / .query(embedding, top_k) -> matches
    """

    @abstractmethod
    def upsert(
        self,
        document_id: str,
        chunks: List[Chunk],
        dense_embeddings: List[List[float]],
        sparse_weights: Optional[List[Dict[str, float]]] = None
    ) -> List[str]:
        """Upsert chunks and their dense/sparse embeddings into the vector store.

        Returns:
            List of embedding reference IDs.
        """
        pass

    @abstractmethod
    def query_dense(
        self,
        document_id: str,
        query_embedding: List[float],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """Query top-K matches by dense embedding cosine similarity."""
        pass

    @abstractmethod
    def query_sparse(
        self,
        document_id: str,
        query_sparse: Dict[str, float],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """Query top-K matches by sparse lexical score / BM25 term matching."""
        pass

    @abstractmethod
    def query(
        self,
        embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Standard Contract §14 query method."""
        pass
