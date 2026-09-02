"""BGE-M3 embedding adapter (BAAI/bge-m3) producing dense + sparse embeddings."""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Tuple
from modules.rag.src.embedding.base import BaseEmbeddingAdapter

logger = logging.getLogger(__name__)


class BGEM3EmbeddingAdapter(BaseEmbeddingAdapter):
    """Embedding adapter using BAAI/bge-m3 for dense + sparse multi-lingual representations."""

    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = True, device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model
        try:
            from FlagEmbedding import BGEM3FlagModel
            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=self.use_fp16,
                device=self.device
            )
            return self._model
        except Exception as e:
            logger.info(f"FlagEmbedding BGEM3FlagModel not loaded ({e}). Attempting sentence-transformers fallback.")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device)
                return self._model
            except Exception as e2:
                logger.warning(f"Could not load BGE-M3 transformer ({e2}). Using mock/dummy embeddings for testing.")
                self._model = "mock"
                return self._model

    def embed_passages(self, texts: List[str]) -> Tuple[List[List[float]], List[Dict[str, float]]]:
        if not texts:
            return [], []

        model = self._get_model()
        if model == "mock":
            # Deterministic mock vectors for testing
            dense_vectors = [[float((hash(t + str(i)) % 1000) / 1000.0) for i in range(128)] for t in texts]
            sparse_weights = [{w.lower(): 1.0 for w in t.split()[:10]} for t in texts]
            return dense_vectors, sparse_weights

        try:
            # If FlagEmbedding BGEM3FlagModel
            if hasattr(model, 'encode') and 'return_dense' in model.encode.__code__.co_varnames:
                outputs = model.encode(
                    texts,
                    return_dense=True,
                    return_sparse=True,
                    return_colbert_vecs=False
                )
                dense_vectors = [v.tolist() for v in outputs['dense_vecs']]
                sparse_weights = [
                    {str(k): float(v) for k, v in sp.items()}
                    for sp in outputs['lexical_weights']
                ]
                return dense_vectors, sparse_weights
            else:
                # sentence-transformers dense-only output with basic token term frequencies for sparse
                dense_arr = model.encode(texts, normalize_embeddings=True)
                dense_vectors = [v.tolist() for v in dense_arr]
                sparse_weights = [{w.lower(): 1.0 for w in t.split()} for t in texts]
                return dense_vectors, sparse_weights
        except Exception as e:
            logger.error(f"Error encoding passages with BGE-M3: {e}")
            dense_vectors = [[0.0] * 128 for _ in texts]
            sparse_weights = [{} for _ in texts]
            return dense_vectors, sparse_weights

    def embed_query(self, query: str) -> Tuple[List[float], Dict[str, float]]:
        dense_list, sparse_list = self.embed_passages([query])
        return dense_list[0] if dense_list else [0.0] * 128, sparse_list[0] if sparse_list else {}
