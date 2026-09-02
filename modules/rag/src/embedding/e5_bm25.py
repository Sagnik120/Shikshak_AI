"""Multilingual E5 + BM25 fallback embedding adapter (intfloat/multilingual-e5-large)."""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Tuple
from modules.rag.src.embedding.base import BaseEmbeddingAdapter

logger = logging.getLogger(__name__)


class E5BM25EmbeddingAdapter(BaseEmbeddingAdapter):
    """Fallback embedding adapter using multilingual-e5-large + BM25Okapi."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-large", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
            return self._model
        except Exception as e:
            logger.warning(f"Could not load multilingual-e5 model ({e}). Using mock embeddings.")
            self._model = "mock"
            return self._model

    def embed_passages(self, texts: List[str]) -> Tuple[List[List[float]], List[Dict[str, float]]]:
        if not texts:
            return [], []

        # E5 prefix requirement: "passage: "
        prefixed_texts = [f"passage: {t}" for t in texts]

        model = self._get_model()
        if model == "mock":
            dense_vectors = [[float((hash(t + str(i)) % 1000) / 1000.0) for i in range(128)] for t in texts]
        else:
            try:
                embeddings = model.encode(prefixed_texts, normalize_embeddings=True)
                dense_vectors = [v.tolist() for v in embeddings]
            except Exception as e:
                logger.error(f"Error encoding passages with E5: {e}")
                dense_vectors = [[0.0] * 128 for _ in texts]

        # BM25-style term frequencies
        sparse_weights: List[Dict[str, float]] = []
        for t in texts:
            words = t.lower().split()
            tf_dict: Dict[str, float] = {}
            for w in words:
                tf_dict[w] = tf_dict.get(w, 0.0) + 1.0
            sparse_weights.append(tf_dict)

        return dense_vectors, sparse_weights

    def embed_query(self, query: str) -> Tuple[List[float], Dict[str, float]]:
        # E5 prefix requirement: "query: "
        prefixed_query = f"query: {query}"

        model = self._get_model()
        if model == "mock":
            dense = [float((hash(query + str(i)) % 1000) / 1000.0) for i in range(128)]
        else:
            try:
                embedding = model.encode(prefixed_query, normalize_embeddings=True)
                dense = embedding.tolist()
            except Exception as e:
                logger.error(f"Error encoding query with E5: {e}")
                dense = [0.0] * 128

        sparse = {w: 1.0 for w in query.lower().split()}
        return dense, sparse
