"""Core benchmark runner for RAG pipeline evaluation.

Orchestrates document ingestion, query execution, metrics collection,
and report generation for benchmark test suites.
"""

from __future__ import annotations

import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from modules.rag.src.service import RAGService
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.embedding.factory import get_embedding_adapter
from modules.rag.src.perf import begin_trace, end_trace

from modules.rag.tests.benchmark.metrics import QueryResult, BenchmarkReport
from modules.rag.tests.benchmark.test_suites import (
    BenchmarkSuite, BenchmarkDocument, BenchmarkQuery, get_suite, list_suites
)

logger = logging.getLogger(__name__)


class BenchmarkEngine:
    """Runs benchmark suites against the production RAG pipeline."""

    def __init__(self):
        # Each benchmark run gets a fresh in-memory vector store
        self._vector_store: Optional[ChromaVectorStoreAdapter] = None
        self._service: Optional[RAGService] = None
        self._ingested_doc_ids: set[str] = set()

    def _init_service(self) -> RAGService:
        """Initialize a fresh RAG service with in-memory vector store."""
        self._vector_store = ChromaVectorStoreAdapter(persist_dir=":memory:")
        embedding_adapter = get_embedding_adapter()
        self._service = RAGService(
            vector_store=self._vector_store,
            embedding_adapter=embedding_adapter
        )
        self._ingested_doc_ids.clear()
        return self._service

    def _ingest_documents(self, documents: List[BenchmarkDocument]) -> Dict[str, List[str]]:
        """Ingest benchmark documents and return mapping of doc_id -> chunk_ids."""
        service = self._service
        if service is None:
            service = self._init_service()

        doc_chunk_map: Dict[str, List[str]] = {}

        for doc in documents:
            if doc.document_id in self._ingested_doc_ids:
                continue

            content_bytes = doc.read_bytes()
            parsed = service.ingest_document(
                file_bytes=content_bytes,
                filename=doc.filename,
                mime_type=doc.mime_type,
                document_id=doc.document_id
            )

            chunk_ids = [c.chunk_id for c in parsed.chunks]
            doc_chunk_map[doc.document_id] = chunk_ids
            self._ingested_doc_ids.add(doc.document_id)

            logger.info(
                f"Ingested '{doc.filename}' -> {len(chunk_ids)} chunks "
                f"(doc_id={doc.document_id})"
            )

        return doc_chunk_map

    def run_suite(
        self,
        suite_name: str,
        top_k: int = 5,
        relevance_threshold: float = 0.5001,
        confidence_threshold: float = 0.52,
        progress_callback=None,
        mode: str = "single_pass",
    ) -> BenchmarkReport:
        """Run a complete benchmark suite and return the report.

        Args:
            suite_name: Key of the benchmark suite to run.
            top_k: Number of results to retrieve per query.
            relevance_threshold: Minimum relevance score.
            confidence_threshold: Threshold for 'low' risk classification.
            progress_callback: Optional callable(current, total, query_text) for progress updates.
            mode: "single_pass" (the original retrieve_context) or "agentic"
                (retrieve_context_agentic, which refines a weakly-grounded first
                pass once). Both paths stay available so they can be compared.

        Returns:
            BenchmarkReport with per-query results and aggregated metrics.
        """
        suite = get_suite(suite_name)
        logger.info(f"Starting benchmark suite: {suite.name} ({len(suite.queries)} queries)")

        # Fresh service for each suite run
        self._init_service()

        # Ingest documents
        doc_chunk_map = self._ingest_documents(suite.documents)

        # Use suite-specific config or override with params
        config = {
            "top_k": top_k,
            "relevance_threshold": relevance_threshold,
            "confidence_threshold": confidence_threshold,
            "mode": mode,
        }

        report = BenchmarkReport(
            suite_name=suite.name,
            config=config
        )

        # Run each query
        for idx, query in enumerate(suite.queries):
            if progress_callback:
                progress_callback(idx + 1, len(suite.queries), query.query_text)

            # Determine document_id for this query
            doc_id = suite.documents[0].document_id if suite.documents else None

            # Time the full retrieval
            trace = begin_trace()
            start_time = time.perf_counter()

            if mode == "agentic":
                result = self._service.retrieve_context_agentic(
                    document_id=doc_id,
                    query_text=query.query_text,
                    top_k=top_k,
                    relevance_threshold=relevance_threshold,
                    confidence_threshold=confidence_threshold,
                    topic=suite.name,
                )
            else:
                result = self._service.retrieve_context(
                    document_id=doc_id,
                    query_text=query.query_text,
                    top_k=top_k,
                    relevance_threshold=relevance_threshold,
                    confidence_threshold=confidence_threshold
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            perf = end_trace()

            # Build QueryResult
            retrieved_ids = [c.chunk_id for c in result.chunks]
            retrieved_scores = [c.score for c in result.chunks]
            perf_stages = perf.to_dict() if perf else {}

            qr = QueryResult(
                query_text=query.query_text,
                expected_chunk_ids=query.expected_chunk_ids,
                retrieved_chunk_ids=retrieved_ids,
                retrieved_scores=retrieved_scores,
                latency_ms=elapsed_ms,
                risk_level=result.risk_level,
                has_sufficient_context=result.has_sufficient_context,
                expected_risk_level=query.expected_risk_level,
                perf_stages=perf_stages,
                attempts=getattr(result, "attempts", 1),
                refined_query=getattr(result, "refined_query", None),
            )

            report.query_results.append(qr)
            logger.info(
                f"  [{idx+1}/{len(suite.queries)}] "
                f"P@K={qr.precision_at_k:.2f} RR={qr.reciprocal_rank:.2f} "
                f"lat={elapsed_ms:.1f}ms risk={result.risk_level}"
            )

        logger.info(f"Suite '{suite.name}' complete: MRR={report.mrr:.3f} P@K={report.mean_precision:.3f}")
        return report

    def run_all_suites(self, **kwargs) -> Dict[str, BenchmarkReport]:
        """Run all available benchmark suites and return results."""
        results = {}
        for key in list_suites():
            report = self.run_suite(key["key"], **kwargs)
            results[key["key"]] = report
        return results

    @staticmethod
    def save_report(report: BenchmarkReport, output_dir: str) -> str:
        """Save a benchmark report to JSON file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_{report.suite_name.replace(' ', '_').lower()}_{timestamp}.json"
        filepath = output_path / filename

        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info(f"Report saved: {filepath}")
        return str(filepath)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    engine = BenchmarkEngine()
    suite_name = sys.argv[1] if len(sys.argv) > 1 else "physics"

    if suite_name == "all":
        results = engine.run_all_suites()
        for key, report in results.items():
            print(f"\n{'='*60}")
            print(f"Suite: {report.suite_name}")
            print(json.dumps(report.to_dict()["metrics"], indent=2))
            print(json.dumps(report.to_dict()["latency"], indent=2))
            targets = report.passes_production_targets()
            print(f"Production targets: {targets}")
    else:
        report = engine.run_suite(suite_name)
        print(json.dumps(report.to_dict(), indent=2))
        output_dir = str(Path(__file__).parent / "results")
        engine.save_report(report, output_dir)
