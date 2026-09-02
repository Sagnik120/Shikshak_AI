"""Embedding adapter factory for selecting and configuring embedding engines."""

from __future__ import annotations

import logging
from typing import Optional

from modules.rag.src.embedding.base import BaseEmbeddingAdapter
from modules.rag.src.embedding.bge_m3 import BGEM3EmbeddingAdapter
from modules.rag.src.embedding.e5_bm25 import E5BM25EmbeddingAdapter

logger = logging.getLogger(__name__)

_DEFAULT_ADAPTER: Optional[BaseEmbeddingAdapter] = None


def get_embedding_adapter(model_type: str = "bge-m3", device: str = "cpu") -> BaseEmbeddingAdapter:
    """Retrieve or instantiate the requested embedding adapter."""
    global _DEFAULT_ADAPTER
    if _DEFAULT_ADAPTER is not None:
        return _DEFAULT_ADAPTER

    if model_type.lower() == "e5":
        _DEFAULT_ADAPTER = E5BM25EmbeddingAdapter(device=device)
    else:
        # Default primary: BGE-M3
        _DEFAULT_ADAPTER = BGEM3EmbeddingAdapter(device=device)

    return _DEFAULT_ADAPTER
