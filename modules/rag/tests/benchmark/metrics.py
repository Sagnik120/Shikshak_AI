"""RAG retrieval quality metrics: Precision@K, Recall@K, MRR, NDCG@K, and latency stats.

Implements standard information retrieval evaluation metrics for benchmarking
the production RAG pipeline quality and performance.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class QueryResult:
    """Result of a single benchmark query evaluation."""
    query_text: str
    expected_chunk_ids: List[str]
    retrieved_chunk_ids: List[str]
    retrieved_scores: List[float]
    latency_ms: float
    risk_level: str
    has_sufficient_context: bool
    expected_risk_level: Optional[str] = None
    perf_stages: Dict[str, float] = field(default_factory=dict)

    @property
    def precision_at_k(self) -> float:
        """Precision@K: fraction of retrieved chunks that are relevant."""
        if not self.retrieved_chunk_ids:
            return 0.0
        relevant_retrieved = sum(1 for c in self.retrieved_chunk_ids if c in self.expected_chunk_ids)
        return relevant_retrieved / len(self.retrieved_chunk_ids)

    @property
    def recall_at_k(self) -> float:
        """Recall@K: fraction of relevant chunks that were retrieved."""
        if not self.expected_chunk_ids:
            return 1.0  # No expected chunks means nothing to miss
        relevant_retrieved = sum(1 for c in self.retrieved_chunk_ids if c in self.expected_chunk_ids)
        return relevant_retrieved / len(self.expected_chunk_ids)

    @property
    def reciprocal_rank(self) -> float:
        """Reciprocal Rank: 1/position of the first relevant result."""
        for i, chunk_id in enumerate(self.retrieved_chunk_ids):
            if chunk_id in self.expected_chunk_ids:
                return 1.0 / (i + 1)
        return 0.0

    @property
    def ndcg_at_k(self) -> float:
        """NDCG@K: Normalized Discounted Cumulative Gain."""
        if not self.expected_chunk_ids:
            return 1.0

        # DCG: sum of (relevance / log2(position + 1)) for retrieved results
        dcg = 0.0
        for i, chunk_id in enumerate(self.retrieved_chunk_ids):
            rel = 1.0 if chunk_id in self.expected_chunk_ids else 0.0
            dcg += rel / math.log2(i + 2)  # i+2 because log2(1) = 0

        # Ideal DCG: perfect ordering
        ideal_relevant = min(len(self.expected_chunk_ids), len(self.retrieved_chunk_ids))
        idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_relevant))

        return dcg / idcg if idcg > 0 else 0.0

    @property
    def risk_match(self) -> bool:
        """Whether the actual risk level matches expected."""
        if self.expected_risk_level is None:
            return True
        return self.risk_level == self.expected_risk_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_text": self.query_text,
            "expected_chunk_ids": self.expected_chunk_ids,
            "retrieved_chunk_ids": self.retrieved_chunk_ids,
            "retrieved_scores": [round(s, 4) for s in self.retrieved_scores],
            "latency_ms": round(self.latency_ms, 2),
            "risk_level": self.risk_level,
            "expected_risk_level": self.expected_risk_level,
            "has_sufficient_context": self.has_sufficient_context,
            "precision_at_k": round(self.precision_at_k, 4),
            "recall_at_k": round(self.recall_at_k, 4),
            "reciprocal_rank": round(self.reciprocal_rank, 4),
            "ndcg_at_k": round(self.ndcg_at_k, 4),
            "risk_match": self.risk_match,
            "perf_stages": {k: round(v, 2) for k, v in self.perf_stages.items()},
        }


@dataclass
class BenchmarkReport:
    """Aggregated benchmark results across all queries in a test suite."""
    suite_name: str
    query_results: List[QueryResult] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    @property
    def num_queries(self) -> int:
        return len(self.query_results)

    @property
    def mean_precision(self) -> float:
        if not self.query_results:
            return 0.0
        return statistics.mean(r.precision_at_k for r in self.query_results)

    @property
    def mean_recall(self) -> float:
        if not self.query_results:
            return 0.0
        return statistics.mean(r.recall_at_k for r in self.query_results)

    @property
    def mrr(self) -> float:
        """Mean Reciprocal Rank across all queries."""
        if not self.query_results:
            return 0.0
        return statistics.mean(r.reciprocal_rank for r in self.query_results)

    @property
    def mean_ndcg(self) -> float:
        if not self.query_results:
            return 0.0
        return statistics.mean(r.ndcg_at_k for r in self.query_results)

    @property
    def risk_accuracy(self) -> float:
        """Fraction of queries where risk classification was correct."""
        applicable = [r for r in self.query_results if r.expected_risk_level is not None]
        if not applicable:
            return 1.0
        return sum(1 for r in applicable if r.risk_match) / len(applicable)

    @property
    def latency_p50(self) -> float:
        lats = sorted(r.latency_ms for r in self.query_results)
        return _percentile(lats, 50)

    @property
    def latency_p95(self) -> float:
        lats = sorted(r.latency_ms for r in self.query_results)
        return _percentile(lats, 95)

    @property
    def latency_p99(self) -> float:
        lats = sorted(r.latency_ms for r in self.query_results)
        return _percentile(lats, 99)

    @property
    def latency_mean(self) -> float:
        if not self.query_results:
            return 0.0
        return statistics.mean(r.latency_ms for r in self.query_results)

    @property
    def throughput_qps(self) -> float:
        """Estimated queries per second based on mean latency."""
        if self.latency_mean <= 0:
            return 0.0
        return 1000.0 / self.latency_mean

    @property
    def stage_latency_breakdown(self) -> Dict[str, float]:
        """Average latency per pipeline stage across all queries."""
        all_stages: Dict[str, List[float]] = {}
        for r in self.query_results:
            for stage, ms in r.perf_stages.items():
                if stage not in all_stages:
                    all_stages[stage] = []
                all_stages[stage].append(ms)
        return {stage: round(statistics.mean(vals), 2) for stage, vals in all_stages.items()}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "config": self.config,
            "num_queries": self.num_queries,
            "metrics": {
                "precision_at_k": round(self.mean_precision, 4),
                "recall_at_k": round(self.mean_recall, 4),
                "mrr": round(self.mrr, 4),
                "ndcg_at_k": round(self.mean_ndcg, 4),
                "risk_accuracy": round(self.risk_accuracy, 4),
            },
            "latency": {
                "p50_ms": round(self.latency_p50, 2),
                "p95_ms": round(self.latency_p95, 2),
                "p99_ms": round(self.latency_p99, 2),
                "mean_ms": round(self.latency_mean, 2),
                "throughput_qps": round(self.throughput_qps, 2),
            },
            "stage_breakdown": self.stage_latency_breakdown,
            "per_query": [r.to_dict() for r in self.query_results],
        }

    # Production target thresholds
    TARGETS = {
        "precision_at_k": 0.60,
        "recall_at_k": 0.50,
        "mrr": 0.70,
        "ndcg_at_k": 0.60,
        "latency_p95_ms": 500.0,
        "risk_accuracy": 0.90,
    }

    def passes_production_targets(self) -> Dict[str, bool]:
        """Check each metric against production-ready thresholds."""
        return {
            "precision_at_k": self.mean_precision >= self.TARGETS["precision_at_k"],
            "recall_at_k": self.mean_recall >= self.TARGETS["recall_at_k"],
            "mrr": self.mrr >= self.TARGETS["mrr"],
            "ndcg_at_k": self.mean_ndcg >= self.TARGETS["ndcg_at_k"],
            "latency_p95": self.latency_p95 <= self.TARGETS["latency_p95_ms"],
            "risk_accuracy": self.risk_accuracy >= self.TARGETS["risk_accuracy"],
        }


def _percentile(sorted_values: List[float], pct: float) -> float:
    """Calculate percentile from sorted list."""
    if not sorted_values:
        return 0.0
    idx = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(sorted_values) - 1)
    frac = idx - lower
    return sorted_values[lower] + frac * (sorted_values[upper] - sorted_values[lower])
