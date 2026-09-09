"""Structured, hierarchical logging engine for ml_core module isolated testing.

Manages fine-grained JSON manifests and human-readable text logs categorized by:
  - evaluation/    (MCQ exact matches, freeform embedding similarity, LLM rubric judge)
  - misconception/ (Subject taxonomy classification, diagnosed conceptual traps)
  - concepts/      (Document chunk term frequency, extracted key concepts)
  - visuals/       (Deterministic rule table matches, LLM visual type suggestions)
  - service/       (MLCoreService facade workflow runs)
  - errors/        (Exceptions, malformed payloads, and fallback triggers)

Explicitly logs the exact source file and function name for full execution traceability.
"""

from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR = DEFAULT_LOGS_DIR


class MLCoreTestLogger:
    """Thread-safe hierarchical logger for isolated ml_core testing."""

    CATEGORIES = ("evaluation", "misconception", "concepts", "visuals", "service", "errors")

    def __init__(self, base_log_dir: Optional[str] = None):
        if base_log_dir:
            self.base_dir = Path(base_log_dir)
        else:
            self.base_dir = DEFAULT_LOGS_DIR

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure all category subdirectories and .gitkeep files exist."""
        for cat in self.CATEGORIES:
            cat_dir = self.base_dir / cat
            cat_dir.mkdir(parents=True, exist_ok=True)
            gitkeep = cat_dir / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()

    def _generate_log_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def _get_timestamp_str(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _write_log(
        self,
        category: str,
        operation: str,
        source_file: str,
        source_function: str,
        status: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Atomic write of both machine-readable JSON and human-friendly .log files."""
        if category not in self.CATEGORIES:
            category = "errors"

        log_id = self._generate_log_id()
        ts_str = self._get_timestamp_str()
        iso_time = datetime.now().isoformat()
        base_filename = f"{ts_str}_{category}_{log_id}"

        target_dir = self.base_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)

        json_path = target_dir / f"{base_filename}.json"
        text_path = target_dir / f"{base_filename}.log"

        payload = {
            "log_id": log_id,
            "timestamp": iso_time,
            "category": category,
            "operation": operation,
            "source": {
                "file": source_file,
                "function": source_function,
            },
            "source_file": source_file,
            "source_function": source_function,
            "status": status,
            "input": input_data,
            "checkpoints": checkpoints or [],
            "output": output_data,
            "error": error_details,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        lines = [
            "=" * 80,
            f"SHIKSHAK AI — ML_CORE TEST LOG: {log_id}",
            f"Category:     {category.upper()}",
            f"Operation:    {operation}",
            f"Status:       {status.upper()}",
            f"Source:       {source_file} :: {source_function}()",
            f"Timestamp:    {iso_time}",
            "=" * 80,
            "",
            "[INPUT PAYLOAD]",
            json.dumps(input_data, indent=2, ensure_ascii=False),
            "",
        ]

        if checkpoints:
            lines.append("[EXECUTION CHECKPOINTS]")
            for cp in checkpoints:
                ts = cp.get("time", "")
                name = cp.get("event", "checkpoint")
                details = cp.get("details", {})
                lines.append(f"-> [{ts}] {name}")
                lines.append(json.dumps(details, indent=2, ensure_ascii=False))
            lines.append("")

        if error_details:
            lines.append("[ERROR TRACE]")
            lines.append(json.dumps(error_details, indent=2, ensure_ascii=False))
            lines.append("")

        lines.append("[OUTPUT PAYLOAD]")
        lines.append(json.dumps(output_data, indent=2, ensure_ascii=False))
        lines.append("")

        with open(text_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return {
            "log_id": log_id,
            "json_path": str(json_path),
            "log_path": str(text_path),
            "relative_json": f"logs/{category}/{base_filename}.json",
            "relative_log": f"logs/{category}/{base_filename}.log",
            "source_file": source_file,
            "source_function": source_function,
        }

    # -------------------------------------------------------------------------
    # Specialized Logging Methods
    # -------------------------------------------------------------------------

    def log_evaluation(
        self,
        node_id: str,
        response_type: str,
        raw_answer: str,
        expected_concept: str,
        grounding_text: Optional[str],
        correct: bool,
        partial_credit: float,
        confidence: float,
        feedback_text: str,
        evaluation_tier: str,
        misconception_tag: Optional[str] = None,
        status: str = "success",
        source_file: str = "modules/ml_core/src/answer_evaluation/evaluator.py",
        source_function: str = "evaluate",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs student response evaluation runs."""
        input_data = {
            "node_id": node_id,
            "response_type": response_type,
            "raw_answer": raw_answer,
            "expected_concept": expected_concept,
            "grounding_text": grounding_text,
        }
        output_data = {
            "correct": correct,
            "partial_credit": partial_credit,
            "confidence": confidence,
            "feedback_text": feedback_text,
            "evaluation_tier": evaluation_tier,
            "misconception_tag": misconception_tag,
            "status": status,
        }
        return self._write_log(
            category="evaluation",
            operation="answer_evaluation",
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_data,
            output_data=output_data,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_misconception(
        self,
        raw_answer: str,
        expected_concept: str,
        subject: str,
        diagnosed_tag: Optional[str],
        taxonomy_size: int,
        status: str = "success",
        source_file: str = "modules/ml_core/src/misconception/classifier.py",
        source_function: str = "classify",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs misconception classification runs."""
        input_data = {
            "raw_answer": raw_answer,
            "expected_concept": expected_concept,
            "subject": subject,
        }
        output_data = {
            "diagnosed_tag": diagnosed_tag,
            "taxonomy_entries_checked": taxonomy_size,
            "status": status,
        }
        return self._write_log(
            category="misconception",
            operation="misconception_classification",
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_data,
            output_data=output_data,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_concepts(
        self,
        chunk_count: int,
        top_k: int,
        extracted_concepts: List[str],
        status: str = "success",
        source_file: str = "modules/ml_core/src/concept_extraction/extractor.py",
        source_function: str = "extract_concepts",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs concept and key-term extraction runs."""
        input_data = {
            "chunk_count": chunk_count,
            "top_k": top_k,
        }
        output_data = {
            "extracted_concepts": extracted_concepts,
            "concept_count": len(extracted_concepts),
            "status": status,
        }
        return self._write_log(
            category="concepts",
            operation="concept_extraction",
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_data,
            output_data=output_data,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_visuals(
        self,
        subject: str,
        concept: str,
        suggested_visual_type: str,
        decision_path: str,
        status: str = "success",
        source_file: str = "modules/ml_core/src/visual_suggestion/suggester.py",
        source_function: str = "suggest",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs visual modality recommendation runs."""
        input_data = {
            "subject": subject,
            "concept": concept,
        }
        output_data = {
            "suggested_visual_type": suggested_visual_type,
            "decision_path": decision_path,
            "status": status,
        }
        return self._write_log(
            category="visuals",
            operation="visual_type_suggestion",
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_data,
            output_data=output_data,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_service(
        self,
        operation: str,
        input_payload: Dict[str, Any],
        output_payload: Dict[str, Any],
        status: str = "success",
        source_file: str = "modules/ml_core/src/service.py",
        source_function: str = "execute",
        checkpoints: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs high-level MLCoreService facade operations."""
        return self._write_log(
            category="service",
            operation=operation,
            source_file=source_file,
            source_function=source_function,
            status=status,
            input_data=input_payload,
            output_data=output_payload,
            checkpoints=checkpoints,
            error_details=error_details,
        )

    def log_error(
        self,
        operation: str,
        error: Exception,
        input_payload: Dict[str, Any],
        source_file: str,
        source_function: str,
    ) -> Dict[str, str]:
        """Logs unhandled exceptions and failures."""
        tb = traceback.format_exc()
        error_details = {
            "exception_type": type(error).__name__,
            "message": str(error),
            "traceback": tb,
        }
        return self._write_log(
            category="errors",
            operation=operation,
            source_file=source_file,
            source_function=source_function,
            status="error",
            input_data=input_payload,
            output_data={},
            error_details=error_details,
        )

    # -------------------------------------------------------------------------
    # Retrieval Methods for UI Explorer
    # -------------------------------------------------------------------------

    def list_logs(self, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recent log manifests for the web UI log explorer."""
        categories = [category] if category and category in self.CATEGORIES else self.CATEGORIES
        results = []

        for cat in categories:
            cat_dir = self.base_dir / cat
            if not cat_dir.exists():
                continue
            for json_file in sorted(cat_dir.glob("*.json"), reverse=True):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    results.append({
                        "log_id": meta.get("log_id"),
                        "timestamp": meta.get("timestamp"),
                        "category": meta.get("category"),
                        "operation": meta.get("operation"),
                        "status": meta.get("status"),
                        "source_file": meta.get("source_file") or meta.get("source", {}).get("file"),
                        "source_function": meta.get("source_function") or meta.get("source", {}).get("function"),
                        "filename": json_file.name,
                        "log_filename": json_file.with_suffix(".log").name,
                    })
                except Exception:
                    continue

        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]

    def get_log(self, category: str, filename: str) -> Optional[Dict[str, Any]]:
        """Retrieves raw JSON or parsed content of a specific log file."""
        if category not in self.CATEGORIES:
            return None

        # Prevent directory traversal
        safe_name = Path(filename).name
        target = self.base_dir / category / safe_name
        if not target.exists():
            return None

        if target.suffix == ".json":
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        elif target.suffix == ".log":
            with open(target, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        return None
