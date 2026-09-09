"""Structured logging engine for the RAG isolated web testbed.

Produces categorized JSON manifests and formatted text logs in
modules/rag/tests/web_test/logs/<category>/ for tracing every input,
source file, function checkpoint, and hallucination risk signal.
"""

from __future__ import annotations

import os
import json
import uuid
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rag_web_test_logger")

BASE_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

CATEGORIES = [
    "parsing",
    "chunking",
    "embedding",
    "indexing",
    "retrieval",
    "grounding",
    "errors",
]


class RAGTestRun:
    """Represents an active or completed diagnostic logging session."""

    def __init__(
        self,
        category: str,
        source_file: str,
        function_name: str,
        input_payload: Dict[str, Any],
        run_id: Optional[str] = None
    ):
        if category not in CATEGORIES:
            category = "errors"
        self.category = category
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.source_file = source_file
        self.function_name = function_name
        self.input_payload = input_payload
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.status = "IN_PROGRESS"
        self.steps: List[Dict[str, Any]] = []
        self.output_payload: Dict[str, Any] = {}
        self.hallucination_audit: Dict[str, Any] = {
            "is_hallucinating": False,
            "hallucinated_chunk_references": [],
            "empty_citations_despite_context": False,
            "hallucination_source_file": None,
            "hallucination_source_function": None,
            "diagnostic_message": None
        }
        self.error_details: Optional[Dict[str, Any]] = None

    def add_step(self, checkpoint_name: str, step_data: Dict[str, Any]):
        """Record an intermediate execution checkpoint."""
        self.steps.append({
            "timestamp": datetime.now().isoformat(),
            "checkpoint": checkpoint_name,
            "data": step_data
        })

    def record_hallucination_risk(
        self,
        hallucinated_chunk_ids: List[str],
        empty_citations: bool,
        source_file: str,
        source_function: str,
        message: str
    ):
        """Explicitly record a detected hallucination risk."""
        self.hallucination_audit = {
            "is_hallucinating": bool(hallucinated_chunk_ids or empty_citations),
            "hallucinated_chunk_references": hallucinated_chunk_ids,
            "empty_citations_despite_context": empty_citations,
            "hallucination_source_file": source_file,
            "hallucination_source_function": source_function,
            "diagnostic_message": message
        }

    def complete(self, output_payload: Dict[str, Any]):
        """Mark run as successful and write manifests."""
        self.end_time = datetime.now()
        self.status = "SUCCESS"
        self.output_payload = output_payload
        self._write_files()

    def fail(self, error: Exception, custom_message: Optional[str] = None):
        """Mark run as failed and write error manifest."""
        self.end_time = datetime.now()
        self.status = "ERROR"
        tb_str = traceback.format_exc()
        self.error_details = {
            "exception_type": type(error).__name__,
            "message": custom_message or str(error),
            "traceback": tb_str.splitlines()
        }
        # Force category to errors if not already
        self.category = "errors"
        self._write_files()

    def to_dict(self) -> Dict[str, Any]:
        duration_ms = 0.0
        if self.end_time:
            duration_ms = (self.end_time - self.start_time).total_seconds() * 1000.0

        return {
            "run_id": self.run_id,
            "category": self.category,
            "status": self.status,
            "source_file": self.source_file,
            "function_name": self.function_name,
            "timestamp": self.start_time.isoformat(),
            "duration_ms": round(duration_ms, 2),
            "input_payload": self._sanitize(self.input_payload),
            "output_payload": self._sanitize(self.output_payload),
            "steps": [
                {
                    "timestamp": s["timestamp"],
                    "checkpoint": s["checkpoint"],
                    "data": self._sanitize(s["data"])
                }
                for s in self.steps
            ],
            "hallucination_audit": self.hallucination_audit,
            "error_details": self.error_details
        }

    def _sanitize(self, data: Any) -> Any:
        """Truncate massive arrays or byte streams to prevent bloated logs."""
        if isinstance(data, dict):
            return {k: self._sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            if len(data) > 50:
                return [self._sanitize(x) for x in data[:50]] + [f"... ({len(data) - 50} more items)"]
            return [self._sanitize(x) for x in data]
        elif isinstance(data, bytes):
            return f"<bytes: length={len(data)}>"
        elif isinstance(data, str) and len(data) > 10000:
            return data[:10000] + f"... [truncated {len(data)-10000} chars]"
        return data

    def _write_files(self):
        """Save JSON manifest and formatted text log to disk."""
        target_dir = os.path.join(BASE_LOG_DIR, self.category)
        os.makedirs(target_dir, exist_ok=True)

        prefix = self.start_time.strftime("%Y%m%d_%H%M%S")
        filename_base = f"{prefix}_{self.category}_{self.run_id}"

        # 1. JSON Manifest
        json_path = os.path.join(target_dir, f"{filename_base}.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write RAG JSON log: {e}")

        # 2. Formatted Text Log
        log_path = os.path.join(target_dir, f"{filename_base}.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(f"SHIKSHAK AI — RAG TEST LOG: {self.run_id}\n")
                f.write(f"Category:     {self.category.upper()}\n")
                f.write(f"Status:       {self.status}\n")
                f.write(f"Source:       {self.source_file} :: {self.function_name}()\n")
                f.write(f"Timestamp:    {self.start_time.isoformat()}\n")
                f.write("=" * 80 + "\n\n")

                f.write("[INPUT PAYLOAD]\n")
                f.write(json.dumps(self._sanitize(self.input_payload), indent=2) + "\n\n")

                if self.steps:
                    f.write("[EXECUTION CHECKPOINTS]\n")
                    for s in self.steps:
                        f.write(f"-> [{s['timestamp']}] {s['checkpoint']}\n")
                        f.write(json.dumps(self._sanitize(s['data']), indent=2) + "\n\n")

                if self.hallucination_audit.get("is_hallucinating"):
                    f.write("!" * 80 + "\n")
                    f.write("[HALLUCINATION RISK DETECTED]\n")
                    f.write(f"Source:  {self.hallucination_audit['hallucination_source_file']} :: {self.hallucination_audit['hallucination_source_function']}()\n")
                    f.write(f"Message: {self.hallucination_audit['diagnostic_message']}\n")
                    f.write(f"Invalid Chunk IDs: {self.hallucination_audit['hallucinated_chunk_references']}\n")
                    f.write("!" * 80 + "\n\n")

                if self.error_details:
                    f.write("!" * 80 + "\n")
                    f.write("[ERROR TRACEBACK]\n")
                    f.write(f"Type: {self.error_details['exception_type']}\n")
                    f.write(f"Message: {self.error_details['message']}\n")
                    f.write("\n".join(self.error_details['traceback']) + "\n")
                    f.write("!" * 80 + "\n\n")

                f.write("[OUTPUT PAYLOAD]\n")
                f.write(json.dumps(self._sanitize(self.output_payload), indent=2) + "\n")
        except Exception as e:
            logger.error(f"Failed to write RAG text log: {e}")


class RAGTestLogger:
    """Factory and query manager for RAG diagnostic test logging."""

    @staticmethod
    def start_run(
        category: str,
        source_file: str,
        function_name: str,
        input_payload: Dict[str, Any]
    ) -> RAGTestRun:
        """Initialize a new diagnostic test run."""
        return RAGTestRun(
            category=category,
            source_file=source_file,
            function_name=function_name,
            input_payload=input_payload
        )

    @staticmethod
    def list_recent_logs(category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve summaries of recent test runs across categories."""
        categories_to_check = [category] if category and category in CATEGORIES else CATEGORIES
        summaries: List[Dict[str, Any]] = []

        for cat in categories_to_check:
            cat_dir = os.path.join(BASE_LOG_DIR, cat)
            if not os.path.exists(cat_dir):
                continue

            for fname in os.listdir(cat_dir):
                if not fname.endswith(".json"):
                    continue

                full_path = os.path.join(cat_dir, fname)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    summaries.append({
                        "run_id": data.get("run_id"),
                        "category": data.get("category"),
                        "status": data.get("status"),
                        "source_file": data.get("source_file"),
                        "function_name": data.get("function_name"),
                        "timestamp": data.get("timestamp"),
                        "duration_ms": data.get("duration_ms"),
                        "is_hallucinating": data.get("hallucination_audit", {}).get("is_hallucinating", False),
                        "filename": fname
                    })
                except Exception:
                    continue

        # Sort by timestamp descending
        summaries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return summaries[:limit]

    @staticmethod
    def get_log_detail(category: str, filename: str) -> Optional[Dict[str, Any]]:
        """Read full JSON log detail by category and filename."""
        if category not in CATEGORIES:
            return None
        target_path = os.path.join(BASE_LOG_DIR, category, filename)
        if not os.path.exists(target_path):
            return None
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
