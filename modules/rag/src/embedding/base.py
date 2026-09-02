"""Abstract interface for embedding adapters (dense + sparse)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple


class BaseEmbeddingAdapter(ABC):
    """Abstract embedding adapter providing unified dense and sparse embedding outputs."""

    @abstractmethod
    def embed_passages(self, texts: List[str]) -> Tuple[List[List[float]], List[Dict[str, float]]]:
        """Embed a batch of passage texts.

        Returns:
            Tuple of (dense_vectors, sparse_lexical_weights)
            - dense_vectors: list of float vectors (e.g. 1024-dim)
            - sparse_lexical_weights: list of token_id/word -> weight mappings
        """
        pass

    @abstractmethod
    def embed_query(self, query: str) -> Tuple[List[float], Dict[str, float]]:
        """Embed a single query string.

        Returns:
            Tuple of (dense_vector, sparse_lexical_weights)
        """
        pass
