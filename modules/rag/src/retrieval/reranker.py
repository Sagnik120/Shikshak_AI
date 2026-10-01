"""Cross-encoder reranker using BAAI/bge-reranker-v2-m3."""

from __future__ import annotations

import os
# Mitigate Windows threading/runtime access violations during CrossEncoder load
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

import logging
import re
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_SUFFIXES = ("ing", "ed", "es", "s")


def _stem(word: str) -> str:
    """Tiny suffix stripper so "laws"/"law" and "forces"/"force" match."""
    for suffix in _SUFFIXES:
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _content_terms(text: str) -> set:
    from modules.rag.src.retrieval.query_preprocessor import _QUERY_STOPWORDS

    return {
        _stem(w)
        for w in _TOKEN_RE.findall(text.lower())
        if len(w) >= 3 and w not in _QUERY_STOPWORDS and not w.isdigit()
    }


def lexical_relevance(query: str, text: str, dense_score: Optional[float] = None) -> float:
    """Calibrated relevance in [0, 1] for when the cross-encoder is off.

    Mirrors the sigmoid scale the retriever's thresholds were tuned on
    (<= 0.5001 = not relevant, >= 0.52 = confidently relevant), so the same
    thresholds stay meaningful on a small host. The old fallback added 0.2 per
    raw substring hit, so a score was a word count: stopwords like "a" counted,
    "laws" never matched "law", and a document chunk that clearly covered the
    concept was rejected as ungrounded.

    Driven by coverage — the share of the query's content words the chunk
    contains. A chunk with no shared content word stays below the relevance
    threshold no matter how close the dense vectors are, because small
    embedding models score unrelated text surprisingly high.
    """
    terms = _content_terms(query)
    if not terms:
        return 0.0
    coverage = len(terms & _content_terms(text)) / len(terms)
    dense = max(0.0, min(1.0, float(dense_score or 0.0)))
    if coverage == 0.0:
        return round(0.45 * dense, 4)
    return round(min(1.0, 0.40 + 0.50 * coverage + 0.10 * dense), 4)


class BGEReranker:
    """Second-stage cross-encoder reranker for high-precision grounding context."""

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        # Env-overridable: BAAI/bge-reranker-v2-m3 needs ~1.3 GB resident on top
        # of the embedding model, which does not fit a small instance.
        # RERANKER_ENABLED=false skips the cross-encoder entirely and uses the
        # existing lexical-overlap path instead.
        self.model_name = model_name or os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
        self.device = device or os.getenv("RERANKER_DEVICE", "cpu")
        self.enabled = os.getenv("RERANKER_ENABLED", "true").strip().lower() not in (
            "0", "false", "no", "off",
        )
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model
        if not self.enabled:
            logger.info("Cross-encoder reranking disabled; using lexical overlap fallback.")
            self._model = "fallback"
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
            scored = []
            for c in candidates:
                c_copy = dict(c)
                c_copy["score"] = lexical_relevance(query, c.get("text", ""), c.get("dense_score"))
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
