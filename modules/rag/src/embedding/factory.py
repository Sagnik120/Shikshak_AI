"""Embedding adapter factory for selecting and configuring embedding engines."""

from __future__ import annotations

import logging
import os
from typing import Optional

from modules.rag.src.embedding.base import BaseEmbeddingAdapter
from modules.rag.src.embedding.bge_m3 import BGEM3EmbeddingAdapter
from modules.rag.src.embedding.e5_bm25 import E5BM25EmbeddingAdapter

logger = logging.getLogger(__name__)

_DEFAULT_ADAPTER: Optional[BaseEmbeddingAdapter] = None


def get_embedding_adapter(
    model_type: Optional[str] = None, device: Optional[str] = None
) -> BaseEmbeddingAdapter:
    """Retrieve or instantiate the requested embedding adapter.

    Defaults come from the environment so a memory-constrained host can pick a
    smaller model without a code change:
      EMBEDDING_BACKEND  bge-m3 (default) | e5
      EMBEDDING_MODEL    overrides the model id, e.g. a MiniLM-sized checkpoint
      EMBEDDING_DEVICE   cpu (default)
    BAAI/bge-m3 needs roughly 2.4 GB resident; see docs before deploying it to a
    small instance.
    """
    global _DEFAULT_ADAPTER
    model_type = (model_type or os.getenv("EMBEDDING_BACKEND", "bge-m3")).strip()
    device = (device or os.getenv("EMBEDDING_DEVICE", "cpu")).strip()
    model_name = os.getenv("EMBEDDING_MODEL", "").strip()
    if _DEFAULT_ADAPTER is not None:
        return _DEFAULT_ADAPTER

    if model_type.lower() == "e5":
        _DEFAULT_ADAPTER = (
            E5BM25EmbeddingAdapter(model_name=model_name, device=device)
            if model_name
            else E5BM25EmbeddingAdapter(device=device)
        )
    else:
        # Default primary: BGE-M3
        _DEFAULT_ADAPTER = (
            BGEM3EmbeddingAdapter(model_name=model_name, device=device)
            if model_name
            else BGEM3EmbeddingAdapter(device=device)
        )

    logger.info(
        "Embedding adapter: %s (%s) on %s",
        type(_DEFAULT_ADAPTER).__name__, _DEFAULT_ADAPTER.model_name, device,
    )
    return _DEFAULT_ADAPTER
