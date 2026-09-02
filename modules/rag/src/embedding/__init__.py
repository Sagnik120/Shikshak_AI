"""Embedding package for dense and sparse multilingual representations."""

from modules.rag.src.embedding.base import BaseEmbeddingAdapter
from modules.rag.src.embedding.bge_m3 import BGEM3EmbeddingAdapter
from modules.rag.src.embedding.e5_bm25 import E5BM25EmbeddingAdapter
from modules.rag.src.embedding.factory import get_embedding_adapter

__all__ = [
    "BaseEmbeddingAdapter",
    "BGEM3EmbeddingAdapter",
    "E5BM25EmbeddingAdapter",
    "get_embedding_adapter",
]
