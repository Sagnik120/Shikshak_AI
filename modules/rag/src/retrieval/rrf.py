"""Reciprocal Rank Fusion (RRF) for combining dense and sparse retrieval result lists."""

from __future__ import annotations

from typing import List, Dict, Any


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    k: int = 60,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """Combine multiple ranked candidate lists into a single fused ranked list using RRF.

    Formula: RRF_score(d) = Σ_{r in ranked_lists} (1 / (k + rank(d, r)))

    Args:
        ranked_lists: List of candidate match lists, where each list is sorted by rank.
        k: Smoothing parameter (default 60 per standard RRF literature).
        top_n: Number of top fused candidates to return.

    Returns:
        List of fused chunk dictionaries sorted by descending RRF score.
    """
    scores: Dict[str, float] = {}
    chunk_data: Dict[str, Dict[str, Any]] = {}
    dense_scores: Dict[str, float] = {}
    sparse_scores: Dict[str, float] = {}

    for list_idx, candidate_list in enumerate(ranked_lists):
        is_dense = (list_idx == 0)
        for rank, item in enumerate(candidate_list):
            chunk_id = item["chunk_id"]
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = item

            # 1-indexed rank
            rrf_val = 1.0 / (k + (rank + 1))
            scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_val

            if is_dense:
                dense_scores[chunk_id] = item.get("score", 0.0)
            else:
                sparse_scores[chunk_id] = item.get("score", 0.0)

    # Sort items by accumulated RRF score descending
    sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    fused_results: List[Dict[str, Any]] = []
    for chunk_id, rrf_score in sorted_ids[:top_n]:
        base_item = dict(chunk_data[chunk_id])
        base_item["score"] = rrf_score
        base_item["dense_score"] = dense_scores.get(chunk_id)
        base_item["sparse_score"] = sparse_scores.get(chunk_id)
        fused_results.append(base_item)

    return fused_results
