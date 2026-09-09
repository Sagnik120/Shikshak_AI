"""Isolated FastAPI backend test server for ml_core module.

Runs on dedicated Port 8003.
Production backend (Port 8000) remains 100% untouched.

Provides endpoints to interactively test:
  1. Student Answer Evaluation (MCQ deterministic matching + Freeform semantic / LLM judge)
  2. Misconception Classification against Physics, Math, and CS inventories
  3. Key Concept & Term Frequency Extraction from text chunks
  4. Subject-Aware Visual Type Suggestions (Rule table + LLM fallback)
  5. Hierarchical Structured Log Explorer with exact source file & function tracing
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure repository root is on sys.path and load environment variables
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from modules.ai_agent_orchestration.src.adapters.gemini_adapter import get_llm_adapter
from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
from modules.ml_core.src.answer_evaluation.evaluator import AnswerEvaluator
from modules.ml_core.src.answer_evaluation.mcq_evaluator import evaluate_mcq
from modules.ml_core.src.answer_evaluation.freeform_evaluator import (
    FreeformEvaluator,
    CONFIDENTLY_HIGH_THRESHOLD,
    CONFIDENTLY_LOW_THRESHOLD,
)
from modules.ml_core.src.concept_extraction.extractor import extract_concepts
from modules.ml_core.src.misconception.classifier import MisconceptionClassifier
from modules.ml_core.src.misconception.taxonomy_loader import TaxonomyLoader
from modules.ml_core.src.schemas.evaluation import EvaluationResult
from modules.ml_core.src.service import MLCoreService
from modules.ml_core.src.visual_suggestion.rules import SUBJECT_TO_VISUAL, CONCEPT_TO_VISUAL, get_rule_based_visual
from modules.ml_core.src.visual_suggestion.suggester import VisualTypeSuggester
from modules.ml_core.tests.web_test.logger import MLCoreTestLogger, LOGS_DIR

app = FastAPI(
    title="Shikshak AI — ML Core Isolated Web Testbed",
    description="Interactive evaluation, misconception diagnostics, concept extraction, and visual suggestion studio on Port 8003.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = MLCoreTestLogger()
taxonomy_loader = TaxonomyLoader()

# Initialize LLM Adapter and Service
llm_adapter = get_llm_adapter()
ml_service = MLCoreService(llm_adapter=llm_adapter)
answer_evaluator = AnswerEvaluator(llm_adapter=llm_adapter)
misconception_classifier = MisconceptionClassifier(llm_adapter=llm_adapter, taxonomy_loader=taxonomy_loader)
visual_suggester = VisualTypeSuggester(llm_adapter=llm_adapter)

STATIC_DIR = Path(__file__).resolve().parent / "static"


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------

class EvaluateRequest(BaseModel):
    node_id: str = Field(default="node_demo_001", description="Identifier of the target lesson node")
    response_type: Literal["mcq", "freeform"] = Field(default="freeform", description="Type of question response")
    raw_answer: str = Field(..., description="Student's raw input or explanation")
    expected_concept: str = Field(..., description="Target canonical concept or correct answer key")
    grounding_text: Optional[str] = Field(default=None, description="Optional RAG reference or textbook chunk")
    subject: str = Field(default="physics", description="Subject domain for misconception classification")
    response_time_sec: float = Field(default=10.0, description="Response time in seconds")


class MisconceptionRequest(BaseModel):
    raw_answer: str = Field(..., description="Incorrect student answer to diagnose")
    expected_concept: str = Field(..., description="Target concept student was asked about")
    subject: str = Field(default="physics", description="Subject taxonomy: 'physics', 'math', or 'cs'")


class ConceptsRequest(BaseModel):
    chunk_texts: List[str] = Field(..., description="List of textbook or lesson document text chunks")
    top_k: int = Field(default=8, ge=1, le=30, description="Maximum number of concepts to extract")


class VisualSuggestionRequest(BaseModel):
    subject: str = Field(..., description="Subject domain (e.g. 'math', 'physics', 'computer science')")
    concept: str = Field(..., description="Concept topic or keyword (e.g. 'quadratic formula', 'binary search')")


# -----------------------------------------------------------------------------
# Core Testbed Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/test/status")
async def get_status() -> Dict[str, Any]:
    """Returns engine health, active taxonomies, and rule table metrics on Port 8003."""
    # Discover available taxonomies
    tax_dir = Path(__file__).resolve().parents[2] / "src" / "misconception" / "taxonomy"
    available_taxonomies = []
    if tax_dir.exists():
        for p in tax_dir.glob("*.json"):
            available_taxonomies.append(p.stem)

    return {
        "status": "ready",
        "port": 8003,
        "module": "ml_core",
        "llm_adapter": type(llm_adapter).__name__,
        "evaluation": {
            "supported_types": ["mcq", "freeform"],
            "mcq_method": "deterministic_exact_match",
            "freeform_method": "embedding_similarity_with_llm_judge",
            "confident_high_threshold": CONFIDENTLY_HIGH_THRESHOLD,
            "confident_low_threshold": CONFIDENTLY_LOW_THRESHOLD,
        },
        "misconceptions": {
            "available_taxonomies": available_taxonomies or ["physics", "math", "cs"],
            "classifier_ready": True,
        },
        "concept_extraction": {
            "method": "term_frequency_heuristic_zero_llm",
            "default_top_k": 8,
        },
        "visual_suggestion": {
            "rule_table_entries": len(SUBJECT_TO_VISUAL) + len(CONCEPT_TO_VISUAL),
            "fallback_method": "constrained_llm_prompt",
            "valid_modalities": VisualTypeSuggester.VALID_TYPES,
        },
    }


@app.post("/api/test/evaluate")
async def test_evaluate(req: EvaluateRequest) -> Dict[str, Any]:
    """Test student answer evaluation with confidence scoring, partial credit, and diagnostic logging."""
    try:
        student_resp = StudentResponse(
            node_id=req.node_id,
            response_type=req.response_type,
            raw_answer=req.raw_answer,
            response_time_sec=req.response_time_sec,
        )

        evaluation_tier = "Tier 1: Deterministic Rule Match" if req.response_type == "mcq" else "Tier 2: Semantic Similarity + LLM Rubric Judge"

        # Execute evaluation
        result: EvaluationResult = answer_evaluator.evaluate(
            response=student_resp,
            expected_concept=req.expected_concept,
            grounding_text=req.grounding_text,
        )

        # If answer is incorrect or partially incorrect, run misconception diagnostics
        misconception_tag = None
        if not result.correct:
            misconception_tag = misconception_classifier.classify(
                raw_answer=req.raw_answer,
                expected_concept=req.expected_concept,
                subject=req.subject,
            )
            if misconception_tag:
                result.misconception_tag = misconception_tag
                result.feedback_text += f" [Diagnosed trap: '{misconception_tag}']"

        log_meta = logger.log_evaluation(
            node_id=req.node_id,
            response_type=req.response_type,
            raw_answer=req.raw_answer,
            expected_concept=req.expected_concept,
            grounding_text=req.grounding_text,
            correct=result.correct,
            partial_credit=result.partial_credit,
            confidence=result.confidence,
            feedback_text=result.feedback_text,
            evaluation_tier=evaluation_tier,
            misconception_tag=result.misconception_tag,
            source_file="modules/ml_core/src/answer_evaluation/evaluator.py",
            source_function="evaluate",
        )

        return {
            "success": True,
            "node_id": result.node_id,
            "correct": result.correct,
            "partial_credit": result.partial_credit,
            "confidence": round(result.confidence, 3),
            "feedback_text": result.feedback_text,
            "misconception_tag": result.misconception_tag,
            "evaluation_tier": evaluation_tier,
            "log_id": log_meta["log_id"],
            "log_file": log_meta["relative_log"],
        }
    except Exception as e:
        log_meta = logger.log_error(
            operation="answer_evaluation",
            error=e,
            input_payload=req.model_dump(),
            source_file="modules/ml_core/src/answer_evaluation/evaluator.py",
            source_function="evaluate",
        )
        raise HTTPException(status_code=500, detail={"error": str(e), "log_id": log_meta["log_id"]})


@app.post("/api/test/misconception")
async def test_misconception(req: MisconceptionRequest) -> Dict[str, Any]:
    """Test misconception classification against curated subject taxonomies."""
    try:
        taxonomy = taxonomy_loader.load_taxonomy(req.subject) or []
        tag = misconception_classifier.classify(
            raw_answer=req.raw_answer,
            expected_concept=req.expected_concept,
            subject=req.subject,
        )

        # Find taxonomy entry details if matched
        matched_entry = next((item for item in taxonomy if item.get("tag") == tag), None)

        log_meta = logger.log_misconception(
            raw_answer=req.raw_answer,
            expected_concept=req.expected_concept,
            subject=req.subject,
            diagnosed_tag=tag,
            taxonomy_size=len(taxonomy),
            source_file="modules/ml_core/src/misconception/classifier.py",
            source_function="classify",
        )

        return {
            "success": True,
            "subject": req.subject,
            "diagnosed_tag": tag,
            "taxonomy_entries_checked": len(taxonomy),
            "tag_description": matched_entry.get("description") if matched_entry else None,
            "remediation_hint": matched_entry.get("remediation") if matched_entry else None,
            "log_id": log_meta["log_id"],
            "log_file": log_meta["relative_log"],
        }
    except Exception as e:
        log_meta = logger.log_error(
            operation="misconception_classification",
            error=e,
            input_payload=req.model_dump(),
            source_file="modules/ml_core/src/misconception/classifier.py",
            source_function="classify",
        )
        raise HTTPException(status_code=500, detail={"error": str(e), "log_id": log_meta["log_id"]})


@app.post("/api/test/concepts")
async def test_concepts(req: ConceptsRequest) -> Dict[str, Any]:
    """Test key concept and term frequency extraction from raw document chunks."""
    try:
        concepts = extract_concepts(req.chunk_texts, top_k=req.top_k)

        log_meta = logger.log_concepts(
            chunk_count=len(req.chunk_texts),
            top_k=req.top_k,
            extracted_concepts=concepts,
            source_file="modules/ml_core/src/concept_extraction/extractor.py",
            source_function="extract_concepts",
        )

        return {
            "success": True,
            "chunk_count": len(req.chunk_texts),
            "concept_count": len(concepts),
            "concepts": concepts,
            "log_id": log_meta["log_id"],
            "log_file": log_meta["relative_log"],
        }
    except Exception as e:
        log_meta = logger.log_error(
            operation="concept_extraction",
            error=e,
            input_payload=req.model_dump(),
            source_file="modules/ml_core/src/concept_extraction/extractor.py",
            source_function="extract_concepts",
        )
        raise HTTPException(status_code=500, detail={"error": str(e), "log_id": log_meta["log_id"]})


@app.post("/api/test/visual_suggestion")
async def test_visual_suggestion(req: VisualSuggestionRequest) -> Dict[str, Any]:
    """Test visual modality recommendations using deterministic rule table + LLM fallback."""
    try:
        # Check rule table first
        rule_hit = get_rule_based_visual(req.subject, req.concept)
        if rule_hit:
            decision_path = "Deterministic Rule Table (0ms latency, zero hallucination)"
            suggested_type = rule_hit
        else:
            decision_path = "Constrained LLM Classifier (Ambiguous concept fallback)"
            suggested_type = visual_suggester.suggest(req.subject, req.concept)

        log_meta = logger.log_visuals(
            subject=req.subject,
            concept=req.concept,
            suggested_visual_type=suggested_type,
            decision_path=decision_path,
            source_file="modules/ml_core/src/visual_suggestion/suggester.py",
            source_function="suggest",
        )

        return {
            "success": True,
            "subject": req.subject,
            "concept": req.concept,
            "suggested_visual_type": suggested_type,
            "decision_path": decision_path,
            "log_id": log_meta["log_id"],
            "log_file": log_meta["relative_log"],
        }
    except Exception as e:
        log_meta = logger.log_error(
            operation="visual_type_suggestion",
            error=e,
            input_payload=req.model_dump(),
            source_file="modules/ml_core/src/visual_suggestion/suggester.py",
            source_function="suggest",
        )
        raise HTTPException(status_code=500, detail={"error": str(e), "log_id": log_meta["log_id"]})


# -----------------------------------------------------------------------------
# Log Explorer Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/test/logs")
async def list_logs(category: Optional[str] = Query(None), limit: int = Query(50)) -> Dict[str, Any]:
    """Returns recent log manifests across evaluation, misconception, concepts, visuals, service, errors."""
    items = logger.list_logs(category=category, limit=limit)
    return {"total_logs": len(items), "logs": items}


@app.get("/api/test/logs/{category}/{filename}")
async def get_log(category: str, filename: str) -> Any:
    """Retrieves full content of a specific log file."""
    content = logger.get_log(category=category, filename=filename)
    if content is None:
        raise HTTPException(status_code=404, detail="Log file not found")
    return content


# -----------------------------------------------------------------------------
# Static Mounts
# -----------------------------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("  SHIKSHAK AI — ML_CORE ISOLATED WEB TESTBED")
    print("  Running on: http://localhost:8003")
    print("  Testing Code: modules/ml_core/src/")
    print("  Production Backend (Port 8000) remains 100% untouched.")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8003)
