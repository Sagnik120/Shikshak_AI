"""Lightweight performance instrumentation for RAG pipeline stages.

Provides a @timed decorator and PerfTrace collector to measure stage-level
latency without impacting the hot path when disabled.
"""

from __future__ import annotations

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Thread-local storage for per-request performance traces
_thread_local = threading.local()


@dataclass
class PerfTrace:
    """Collects stage-level latency measurements for a single pipeline invocation."""

    stages: Dict[str, float] = field(default_factory=dict)
    _start_time: Optional[float] = field(default=None, repr=False)

    def start(self) -> None:
        """Mark the start of the pipeline."""
        self._start_time = time.perf_counter()

    def record(self, stage_name: str, duration_ms: float) -> None:
        """Record a stage's duration in milliseconds."""
        self.stages[stage_name] = round(duration_ms, 3)

    @property
    def total_ms(self) -> float:
        """Total elapsed time from start, or sum of stages if start wasn't called."""
        if self._start_time is not None:
            return round((time.perf_counter() - self._start_time) * 1000, 3)
        return round(sum(self.stages.values()), 3)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON output and logging."""
        result = dict(self.stages)
        result["total_ms"] = self.total_ms
        return result

    def __repr__(self) -> str:
        parts = [f"{k}={v:.1f}ms" for k, v in self.stages.items()]
        parts.append(f"total={self.total_ms:.1f}ms")
        return f"PerfTrace({', '.join(parts)})"


def get_current_trace() -> Optional[PerfTrace]:
    """Get the current thread's active PerfTrace, if any."""
    return getattr(_thread_local, "trace", None)


def set_current_trace(trace: Optional[PerfTrace]) -> None:
    """Set or clear the current thread's PerfTrace."""
    _thread_local.trace = trace


def begin_trace() -> PerfTrace:
    """Create and activate a new PerfTrace for the current thread."""
    trace = PerfTrace()
    trace.start()
    set_current_trace(trace)
    return trace


def end_trace() -> Optional[PerfTrace]:
    """Finalize and return the current trace, clearing it from thread-local."""
    trace = get_current_trace()
    set_current_trace(None)
    return trace


def timed(stage_name: str):
    """Decorator that records a function's execution time into the active PerfTrace.

    If no PerfTrace is active, the function executes normally without overhead.

    Usage:
        @timed("embed_query")
        def embed_query(self, query):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            trace = get_current_trace()
            if trace is None:
                return func(*args, **kwargs)

            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                trace.record(stage_name, elapsed_ms)

        return wrapper
    return decorator


class TimedBlock:
    """Context manager for timing a named stage within the active PerfTrace.

    Usage:
        with TimedBlock("rrf_fusion"):
            fused = reciprocal_rank_fusion(...)
    """

    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self._start: float = 0.0

    def __enter__(self) -> "TimedBlock":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        trace = get_current_trace()
        if trace is not None:
            trace.record(self.stage_name, elapsed_ms)
