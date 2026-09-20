"""RAG Performance Benchmarking Dashboard — FastAPI Server on Port 8006.

Isolated web service for running RAG benchmarks, viewing metrics,
and comparing pipeline configurations. Does NOT modify production code.
"""

from __future__ import annotations

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from modules.rag.tests.benchmark.benchmark_engine import BenchmarkEngine
from modules.rag.tests.benchmark.test_suites import list_suites, ALL_SUITES
from modules.rag.tests.benchmark.metrics import BenchmarkReport

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("rag_benchmark_server")

app = FastAPI(
    title="RAG Performance Benchmark Dashboard",
    description="Isolated benchmark service for measuring RAG pipeline quality and latency",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# State
_engine = BenchmarkEngine()
_last_reports: Dict[str, Dict[str, Any]] = {}

# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class RunBenchmarkRequest(BaseModel):
    suite: str = Field(default="physics", description="Suite key: physics, rejection, multilingual")
    top_k: int = Field(default=5, ge=1, le=20)
    relevance_threshold: float = Field(default=0.5001)
    confidence_threshold: float = Field(default=0.52)


class CompareRequest(BaseModel):
    suite: str = "physics"
    config_a: Dict[str, Any] = Field(default_factory=lambda: {"top_k": 5})
    config_b: Dict[str, Any] = Field(default_factory=lambda: {"top_k": 10})


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the benchmark dashboard UI."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>RAG Benchmark Dashboard</h1><p>Static files not found.</p>")


@app.get("/api/status")
async def status():
    return {
        "service": "rag_benchmark_dashboard",
        "status": "ok",
        "port": 8006,
        "suites_available": list_suites(),
        "last_reports": list(_last_reports.keys()),
    }


@app.get("/api/suites")
async def get_suites():
    """List all available benchmark suites."""
    return list_suites()


@app.post("/api/run")
async def run_benchmark(req: RunBenchmarkRequest):
    """Run a benchmark suite and return the full report."""
    try:
        global _engine
        _engine = BenchmarkEngine()

        report = _engine.run_suite(
            suite_name=req.suite,
            top_k=req.top_k,
            relevance_threshold=req.relevance_threshold,
            confidence_threshold=req.confidence_threshold,
        )

        report_dict = report.to_dict()
        report_dict["production_targets"] = report.passes_production_targets()

        # Cache and save
        _last_reports[req.suite] = report_dict
        BenchmarkEngine.save_report(report, str(RESULTS_DIR))

        return report_dict

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Benchmark run failed")
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {str(e)}")


@app.post("/api/compare")
async def compare_configs(req: CompareRequest):
    """Run the same suite with two different configs for A/B comparison."""
    try:
        engine_a = BenchmarkEngine()
        engine_b = BenchmarkEngine()

        report_a = engine_a.run_suite(req.suite, **req.config_a)
        report_b = engine_b.run_suite(req.suite, **req.config_b)

        result_a = report_a.to_dict()
        result_b = report_b.to_dict()
        result_a["production_targets"] = report_a.passes_production_targets()
        result_b["production_targets"] = report_b.passes_production_targets()

        return {
            "config_a": req.config_a,
            "config_b": req.config_b,
            "report_a": result_a,
            "report_b": result_b,
        }

    except Exception as e:
        logger.exception("Comparison run failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/last-report/{suite}")
async def get_last_report(suite: str):
    """Get the most recent report for a suite."""
    report = _last_reports.get(suite)
    if not report:
        raise HTTPException(status_code=404, detail=f"No report found for suite '{suite}'")
    return report


@app.get("/api/saved-reports")
async def list_saved_reports():
    """List all saved benchmark report files."""
    reports = []
    for f in sorted(RESULTS_DIR.glob("*.json"), reverse=True):
        try:
            with open(f) as fp:
                data = json.load(fp)
            reports.append({
                "filename": f.name,
                "suite_name": data.get("suite_name", ""),
                "num_queries": data.get("num_queries", 0),
                "metrics": data.get("metrics", {}),
                "latency": data.get("latency", {}),
            })
        except Exception:
            pass
    return reports


@app.get("/api/saved-reports/{filename}")
async def get_saved_report(filename: str):
    """Load a specific saved report."""
    filepath = RESULTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Report '{filename}' not found")
    with open(filepath) as f:
        return json.load(f)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("BENCHMARK_PORT", "8006"))
    logger.info(f"Starting RAG Benchmark Dashboard on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
