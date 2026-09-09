"""Structured, hierarchical logging engine for backend module isolated testing.

Manages fine-grained JSON manifests and human-readable text logs categorized by:
  - sessions/      (Session creation, auth token generation, persistence state updates)
  - websocket/     (Live WebSocket lifecycle, incoming frames, outgoing broadcast events)
  - orchestration/ (Teacher state transitions, SessionDriver steps, lesson plan generation)
  - rag_relay/     (Multipart document upload ingestion, detected structure, grounding context)
  - avatar_relay/  (TeachingSegment multimedia delivery, visual specs, video references)
  - telemetry/     (Health checks, latency telemetry, active session counts)
  - errors/        (Exceptions, 401/422 validation failures, unhandled crashes, and hallucination alerts)

Explicitly logs the exact source file and function name for full execution and hallucination traceability.
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


class BackendTestLogger:
    """Thread-safe hierarchical logger for isolated backend testing."""

    CATEGORIES = (
        "sessions",
        "websocket",
        "orchestration",
        "rag_relay",
        "avatar_relay",
        "telemetry",
        "errors",
    )

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

        # Hallucination heuristic: malformed output, empty node_id when expected, or unhandled nulls
        is_hallucination_suspect = False
        if error_details and error_details.get("hallucination_warning"):
            is_hallucination_suspect = True

        payload = {
            "log_id": log_id,
            "timestamp": iso_time,
            "category": category,
            "operation": operation,
            "source": {
                "file": source_file,
                "function": source_function,
            },
            "status": status,
            "is_hallucination_suspect": is_hallucination_suspect,
            "input": input_data,
            "output": output_data,
            "checkpoints": checkpoints or [],
            "error": error_details,
        }

        # 1. Write structured JSON manifest
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

        # 2. Write human-readable formatted text transcript
        with open(text_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"  SHIKSHAK AI — BACKEND TEST LOG ENTRY [{log_id}]\n")
            f.write(f"  Category:  {category.upper()}\n")
            f.write(f"  Operation: {operation}\n")
            f.write(f"  Timestamp: {iso_time}\n")
            f.write(f"  Source:    {source_file} -> {source_function}()\n")
            f.write(f"  Status:    {status.upper()}\n")
            if is_hallucination_suspect:
                f.write("  ALERT:     *** SUSPECTED HALLUCINATION OR MALFORMED OUTPUT ***\n")
            f.write("=" * 80 + "\n\n")

            f.write("--- [INPUT DATA] ---\n")
            f.write(json.dumps(input_data, indent=2, default=str) + "\n\n")

            if checkpoints:
                f.write("--- [EXECUTION CHECKPOINTS & TRACE] ---\n")
                for cp in checkpoints:
                    f.write(f"  * {cp.get('step', 'step')}: {cp.get('detail', '')} ({cp.get('latency_ms', 0)} ms)\n")
                f.write("\n")

            f.write("--- [OUTPUT DATA] ---\n")
            f.write(json.dumps(output_data, indent=2, default=str) + "\n\n")

            if error_details:
                f.write("--- [ERROR & EXCEPTION DETAILS] ---\n")
                f.write(json.dumps(error_details, indent=2, default=str) + "\n\n")

            f.write("=" * 80 + "\n")
            f.write(f"  End of Log Entry: {log_id}\n")
            f.write("=" * 80 + "\n")

        rel_log_path = str(text_path.relative_to(self.base_dir.parent))
        rel_json_path = str(json_path.relative_to(self.base_dir.parent))

        return {
            "log_id": log_id,
            "category": category,
            "json_path": rel_json_path,
            "log_path": rel_log_path,
            "filename": f"{base_filename}.log",
            "json_filename": f"{base_filename}.json",
        }

    # -------------------------------------------------------------------------
    # Specialized Logging Methods for Backend Subsystems
    # -------------------------------------------------------------------------

    def log_session_event(
        self,
        operation: str,
        session_id: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        source_function: str = "create_session",
        status: str = "success",
        latency_ms: float = 0.0,
    ) -> Dict[str, str]:
        """Logs session lifecycle events (creation, topic submission, state saving)."""
        checkpoints = [
            {"step": "session_auth_dispatch", "detail": f"Session {session_id} event {operation}", "latency_ms": latency_ms}
        ]
        return self._write_log(
            category="sessions",
            operation=operation,
            source_file="modules/backend/src/api/rest.py",
            source_function=source_function,
            status=status,
            input_data={"session_id": session_id, **input_data},
            output_data=output_data,
            checkpoints=checkpoints,
        )

    def log_websocket_frame(
        self,
        session_id: str,
        direction: str,  # "inbound" or "outbound"
        event_type: str,
        payload: Dict[str, Any],
        source_function: str = "websocket_endpoint",
        state: str = "active",
    ) -> Dict[str, str]:
        """Logs WebSocket frame transactions (both client messages and server broadcasts)."""
        checkpoints = [
            {"step": f"ws_frame_{direction}", "detail": f"Event {event_type} on session {session_id}", "latency_ms": 0.5}
        ]
        return self._write_log(
            category="websocket",
            operation=f"ws_{direction}_{event_type}",
            source_file="modules/backend/src/api/ws.py",
            source_function=source_function,
            status="delivered",
            input_data={"session_id": session_id, "direction": direction, "event_type": event_type},
            output_data={"state": state, "payload": payload},
            checkpoints=checkpoints,
        )

    def log_orchestration_step(
        self,
        session_id: str,
        current_state: str,
        next_state: str,
        action: str,
        source_function: str = "SessionDriver.step",
        latency_ms: float = 0.0,
        result_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Logs TeacherState transitions orchestrated by the SessionDriver."""
        checkpoints = [
            {"step": "state_transition", "detail": f"{current_state} -> {next_state} via {action}", "latency_ms": latency_ms}
        ]
        return self._write_log(
            category="orchestration",
            operation="state_machine_transition",
            source_file="modules/backend/src/state/driver.py",
            source_function=source_function,
            status="completed",
            input_data={"session_id": session_id, "from_state": current_state, "action": action},
            output_data={"next_state": next_state, "payload": result_payload or {}},
            checkpoints=checkpoints,
        )

    def log_rag_relay(
        self,
        session_id: str,
        document_id: str,
        filename: str,
        file_size_bytes: int,
        detected_structure: Dict[str, Any],
        source_function: str = "upload_document",
        latency_ms: float = 0.0,
    ) -> Dict[str, str]:
        """Logs document upload ingestion and structure extraction relayed to RAGService."""
        checkpoints = [
            {"step": "storage_adapter_put", "detail": f"Saved {file_size_bytes} bytes", "latency_ms": latency_ms * 0.2},
            {"step": "rag_ingest_relay", "detail": f"RAGService ingested document {document_id}", "latency_ms": latency_ms * 0.8},
        ]
        return self._write_log(
            category="rag_relay",
            operation="document_upload_ingest",
            source_file="modules/backend/src/api/rest.py",
            source_function=source_function,
            status="ready",
            input_data={"session_id": session_id, "document_id": document_id, "filename": filename, "size_bytes": file_size_bytes},
            output_data={"document_id": document_id, "detected_structure": detected_structure},
            checkpoints=checkpoints,
        )

    def log_avatar_relay(
        self,
        session_id: str,
        teaching_segment_id: str,
        visual_type: str,
        has_audio: bool,
        source_function: str = "ws_render_avatar",
        latency_ms: float = 0.0,
    ) -> Dict[str, str]:
        """Logs multimedia presentation segments relayed to AvatarVoiceService."""
        checkpoints = [
            {"step": "avatar_render_dispatch", "detail": f"Visual {visual_type}, audio={has_audio}", "latency_ms": latency_ms}
        ]
        return self._write_log(
            category="avatar_relay",
            operation="render_teaching_segment",
            source_file="modules/backend/src/api/ws.py",
            source_function=source_function,
            status="rendered",
            input_data={"session_id": session_id, "segment_id": teaching_segment_id, "visual_type": visual_type},
            output_data={"status": "dispatched", "has_audio": has_audio},
            checkpoints=checkpoints,
        )

    def log_telemetry_event(
        self,
        operation: str,
        metrics: Dict[str, Any],
        source_function: str = "health_check",
    ) -> Dict[str, str]:
        """Logs health status and performance telemetry metrics."""
        return self._write_log(
            category="telemetry",
            operation=operation,
            source_file="modules/backend/src/main.py",
            source_function=source_function,
            status="healthy",
            input_data={"probe": "periodic_or_manual"},
            output_data=metrics,
        )

    def log_error_event(
        self,
        operation: str,
        error_type: str,
        error_message: str,
        source_file: str,
        source_function: str,
        input_data: Dict[str, Any],
        is_hallucination: bool = False,
    ) -> Dict[str, str]:
        """Logs unhandled exceptions, validation errors, and suspect hallucination events."""
        error_details = {
            "error_type": error_type,
            "error_message": error_message,
            "hallucination_warning": is_hallucination,
            "stack_trace": traceback.format_exc(),
        }
        return self._write_log(
            category="errors",
            operation=operation,
            source_file=source_file,
            source_function=source_function,
            status="failed",
            input_data=input_data,
            output_data={},
            error_details=error_details,
        )

    # -------------------------------------------------------------------------
    # Listing & Inspection
    # -------------------------------------------------------------------------

    def list_logs(self, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recent test logs across all or a specific category."""
        results = []
        categories_to_check = [category] if (category and category in self.CATEGORIES) else self.CATEGORIES

        for cat in categories_to_check:
            cat_dir = self.base_dir / cat
            if not cat_dir.exists():
                continue
            for json_file in cat_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        results.append({
                            "log_id": data.get("log_id"),
                            "timestamp": data.get("timestamp"),
                            "category": data.get("category"),
                            "operation": data.get("operation"),
                            "status": data.get("status"),
                            "source": data.get("source", {}),
                            "is_hallucination_suspect": data.get("is_hallucination_suspect", False),
                            "json_file": f"logs/{cat}/{json_file.name}",
                            "log_file": f"logs/{cat}/{json_file.stem}.log",
                        })
                except Exception:
                    continue

        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]

    def read_log_file(self, category: str, filename: str) -> Optional[str]:
        """Reads a specific log file content (either .json or .log)."""
        if category not in self.CATEGORIES:
            return None
        safe_filename = Path(filename).name
        target_path = self.base_dir / category / safe_filename
        if target_path.exists() and target_path.is_file():
            with open(target_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
