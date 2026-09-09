import os
import sys
import json
import time
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class ExecutionTrace:
    """
    Fine-grained execution trace tracking individual checkpoints, files,
    functions, raw LLM payloads, and errors for an isolated test run.
    """

    def __init__(self, category: str, action: str, inputs: Dict[str, Any], logger_instance: "OrchestrationTestLogger"):
        self.category = category
        self.action = action
        self.inputs = inputs
        self.logger = logger_instance

        self.start_time = time.time()
        self.timestamp = datetime.now().isoformat()
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"run_{date_str}_{action}_{uuid.uuid4().hex[:6]}"

        self.checkpoints: List[Dict[str, Any]] = []
        self.llm_info: Optional[Dict[str, Any]] = None
        self.output_data: Optional[Any] = None
        self.error_info: Optional[Dict[str, Any]] = None
        self.status = "IN_PROGRESS"
        self.duration_ms: float = 0.0

    def add_checkpoint(self, file: str, function: str, step: str, details: Optional[Dict[str, Any]] = None):
        """Record an execution checkpoint with file and function context."""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "file": file,
            "function": function,
            "step": step,
            "details": details or {}
        }
        self.checkpoints.append(checkpoint)

    def set_llm_call(
        self,
        system_prompt: str,
        user_prompt: str,
        raw_response: str,
        model_name: str = "unknown",
        prompt_file: Optional[str] = None
    ):
        """Record the exact LLM prompt and raw string output."""
        self.llm_info = {
            "model": model_name,
            "prompt_file": prompt_file,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_response": raw_response
        }

    def set_output(self, output: Any):
        """Record successful output payload."""
        self.status = "SUCCESS"
        if hasattr(output, "model_dump"):
            self.output_data = output.model_dump()
        elif isinstance(output, dict) or isinstance(output, list) or isinstance(output, (str, int, float, bool)):
            self.output_data = output
        else:
            self.output_data = str(output)

    def set_error(self, exc: Exception):
        """Record failure with complete traceback, file, and line number."""
        self.status = "ERROR"
        tb = traceback.extract_tb(exc.__traceback__)
        last_call = tb[-1] if tb else None

        self.error_info = {
            "type": type(exc).__name__,
            "message": str(exc),
            "file": last_call.filename if last_call else "unknown",
            "line": last_call.lineno if last_call else 0,
            "function": last_call.name if last_call else "unknown",
            "traceback": traceback.format_exc()
        }

    def finish(self) -> Dict[str, Any]:
        """Finalize the trace and persist both JSON manifest and readable log file."""
        self.duration_ms = round((time.time() - self.start_time) * 1000, 2)
        if self.status == "IN_PROGRESS":
            self.status = "COMPLETED"

        manifest = {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "category": self.category,
            "action": self.action,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "inputs": self.inputs,
            "trace": self.checkpoints,
            "llm_call": self.llm_info,
            "output": self.output_data,
            "error": self.error_info
        }

        self.logger._save_trace(self.category, self.run_id, manifest)
        if self.error_info:
            self.logger._save_trace("errors", self.run_id, manifest)

        return manifest


class OrchestrationTestLogger:
    """
    Dedicated structured logging engine for AI Agent Orchestration testing.
    Maintains partitioned directories by category and records full execution traces.
    """

    CATEGORIES = ["planner", "explainer", "questioner", "adaptation", "assessment", "fsm", "errors"]

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(__file__).resolve().parent / "logs"

        self._ensure_directories()

    def _ensure_directories(self):
        """Create structured log directories if they do not exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for cat in self.CATEGORIES:
            cat_dir = self.base_dir / cat
            cat_dir.mkdir(parents=True, exist_ok=True)
            keep_file = cat_dir / ".gitkeep"
            if not keep_file.exists():
                try:
                    keep_file.touch()
                except Exception:
                    pass

    def start_trace(self, category: str, action: str, inputs: Dict[str, Any]) -> ExecutionTrace:
        """Start a new fine-grained execution trace."""
        if category not in self.CATEGORIES:
            category = "fsm"
        return ExecutionTrace(category=category, action=action, inputs=inputs, logger_instance=self)

    def _save_trace(self, category: str, run_id: str, manifest: Dict[str, Any]):
        """Persist JSON manifest and structured text log."""
        cat_dir = self.base_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        json_path = cat_dir / f"{run_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Human-readable log
        log_path = cat_dir / f"{run_id}.log"
        lines = [
            f"==================================================================",
            f" RUN ID     : {manifest['run_id']}",
            f" TIMESTAMP  : {manifest['timestamp']}",
            f" CATEGORY   : {manifest['category']} | ACTION: {manifest['action']}",
            f" STATUS     : {manifest['status']} ({manifest['duration_ms']} ms)",
            f"==================================================================",
            f"\n[INPUTS]:\n{json.dumps(manifest['inputs'], indent=2)}",
            f"\n[EXECUTION CHECKPOINTS]:"
        ]

        for cp in manifest.get("trace", []):
            lines.append(f"  -> [{cp['step']}] in {cp['function']}() ({cp['file']})")
            if cp.get("details"):
                lines.append(f"     Details: {json.dumps(cp['details'])}")

        if manifest.get("llm_call"):
            llm = manifest["llm_call"]
            lines.append(f"\n[LLM INTERACTION - Model: {llm.get('model')}]:")
            lines.append(f"  Prompt File : {llm.get('prompt_file')}")
            lines.append(f"  System Prompt Snippet: {str(llm.get('system_prompt', ''))[:180]}...")
            lines.append(f"  Raw Output Snippet   : {str(llm.get('raw_response', ''))[:250]}...")

        if manifest.get("output"):
            lines.append(f"\n[OUTPUT PAYLOAD]:\n{json.dumps(manifest['output'], indent=2)}")

        if manifest.get("error"):
            err = manifest["error"]
            lines.append(f"\n[ERROR ENCOUNTERED]:")
            lines.append(f"  Error Type: {err.get('type')}")
            lines.append(f"  Message   : {err.get('message')}")
            lines.append(f"  Location  : {err.get('file')}:{err.get('line')} in {err.get('function')}()")
            lines.append(f"  Traceback :\n{err.get('traceback')}")

        lines.append(f"\n==================================================================\n")

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def list_recent_logs(self, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List summary of recent test runs across all categories or a specific category."""
        target_dirs = []
        if category and category in self.CATEGORIES:
            target_dirs.append(self.base_dir / category)
        else:
            for cat in self.CATEGORIES:
                target_dirs.append(self.base_dir / cat)

        entries = []
        for d in target_dirs:
            if not d.exists():
                continue
            for json_file in d.glob("*.json"):
                try:
                    stat = json_file.stat()
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        entries.append({
                            "run_id": data.get("run_id", json_file.stem),
                            "category": data.get("category", d.name),
                            "action": data.get("action", "unknown"),
                            "status": data.get("status", "UNKNOWN"),
                            "timestamp": data.get("timestamp", ""),
                            "duration_ms": data.get("duration_ms", 0),
                            "filename": json_file.name,
                            "has_error": bool(data.get("error")),
                            "mtime": stat.st_mtime
                        })
                except Exception:
                    pass

        # Sort newest first
        entries.sort(key=lambda x: x.get("mtime", 0), reverse=True)
        return entries[:limit]

    def get_log_content(self, category: str, filename: str) -> Optional[Dict[str, Any]]:
        """Retrieve the full JSON content of a specific log."""
        if category not in self.CATEGORIES:
            return None
        safe_filename = Path(filename).name
        target = self.base_dir / category / safe_filename
        if not target.exists() or not target.is_file():
            return None

        try:
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


# Global instance for easy import
test_logger = OrchestrationTestLogger()
