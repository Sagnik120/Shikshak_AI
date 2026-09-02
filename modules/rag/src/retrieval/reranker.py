"""Cross-encoder reranker using BAAI/bge-reranker-v2-m3."""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class BGEReranker:
    """Second-stage cross-encoder reranker for high-precision grounding context."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model
        try:
            from FlagEmbedding import FlagReranker
            self._model = FlagReranker(self.model_name, use_fp16=True, device=self.device)
            return self._model
        except Exception as e:
            logger.info(f"FlagReranker not available ({e}). Trying sentence-transformers CrossEncoder.")
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name, device=self.device)
                return self._model
            except Exception as e2:
                logger.warning(f"Could not load BGE reranker ({e2}). Using lexical/overlap reranking fallback.")
                self._model = "fallback"
                return self._model

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Rerank candidate chunks with cross-encoder score.

        Args:
            query: User/orchestration query string.
            candidates: List of chunk dictionaries (typically from RRF fusion).
            top_k: Number of final reranked chunks to return.

        Returns:
            Sorted list of chunk dictionaries with updated 'score' field.
        """
        if not candidates:
            return []

        model = self._get_model()

        if model == "fallback":
            # Lexical overlap + previous rank fallback
            q_words = set(query.lower().split())
            scored = []
            for c in candidates:
                c_text = c.get("text", "").lower()
                overlap = sum(1 for w in q_words if w in c_text)
                base_score = c.get("score", 0.0)
                combined = (overlap * 0.2) + (base_score * 0.8)
                c_copy = dict(c)
                c_copy["score"] = float(combined)
                scored.append(c_copy)
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:top_k]

        try:
            pairs = [[query, c["text"]] for c in candidates]
            if hasattr(model, 'compute_score'):
                # FlagReranker interface
                scores = model.compute_score(pairs, normalize=True)
                if isinstance(scores, float):
                    scores = [scores]
            else:
                # CrossEncoder interface
                import numpy as np
                raw_scores = model.predict(pairs)
                # Apply sigmoid normalization if needed
                scores = (1 / (1 + np.exp(-raw_scores))).tolist() if hasattr(raw_scores, '__iter__') else [float(raw_scores)]

            reranked = []
            for c, s in zip(candidates, scores):
                c_copy = dict(c)
                c_copy["score"] = float(s)
                reranked.append(c_copy)

            reranked.sort(key=lambda x: x["score"], reverse=True)
            return reranked[:top_k]
        except Exception as e:
            logger.error(f"Error during BGE cross-encoder reranking: {e}")
            return candidates[:top_k]
