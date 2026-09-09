"""Isolated FastAPI backend test server for backend module.

Runs on dedicated Port 8005.
Production backend (Port 8000) remains 100% untouched.

Provides endpoints to interactively test:
  1. Session Lifecycle & Auth Token Generation
  2. Topic Submission & Learner Constraints
  3. Multipart Document Upload & RAG Relay
  4. Curriculum Planning & TeacherState Orchestration
  5. Live WebSocket Bi-Directional Relay Simulator
  6. Hierarchical Structured Log Explorer with exact source file & function tracing
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, WebSocket, WebSocketDisconnect
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

from modules.backend.src.auth import generate_session_token, verify_ws_token
from modules.backend.src.persistence.in_memory import (
    session_repo,
    learner_repo,
    report_repo,
    document_repo,
    storage_adapter,
)
from modules.backend.src.schemas.contract import (
    TopicRequest,
    LessonPlan,
    LearnerConstraints,
    LearnerProfile,
    AssessmentReport,
)
from modules.backend.src.schemas.ws import WSMessage
from modules.backend.src.state.driver import SessionDriver
from modules.backend.src.integrations.container import services
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.backend.tests.web_test.logger import BackendTestLogger, LOGS_DIR

app = FastAPI(
    title="Shikshak AI — Backend Module Isolated Testbed",
    description="Interactive diagnostic studio on Port 8005 testing sessions, REST endpoints, WebSocket relay, and microservice container gateways.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = BackendTestLogger()
STATIC_DIR = Path(__file__).resolve().parent / "static"


# -----------------------------------------------------------------------------
# Request & Response Schemas for the Testbed
# -----------------------------------------------------------------------------

class TestSessionResponse(BaseModel):
    session_id: str
    token: str
    status: str
    log_file: Optional[str] = None


class TestTopicRequest(BaseModel):
    session_id: str
    topic: str
    level: str = "beginner"
    language: str = "en"
    time_budget_min: int = 15


class TestPlanRequest(BaseModel):
    session_id: str


# -----------------------------------------------------------------------------
# Core Diagnostic Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/test/status")
async def get_status() -> Dict[str, Any]:
    """Returns engine health, active sessions, and gateway connectivity metrics."""
    # Count sessions in repo
    session_count = len(getattr(session_repo, "sessions", {}))
    doc_count = len(getattr(document_repo, "documents", {}))
    profile_count = len(getattr(learner_repo, "profiles", {}))

    from modules.ai_agent_orchestration.src.adapters.gemini_adapter import get_llm_adapter
    active_adapter = get_llm_adapter()
    adapter_name = type(active_adapter).__name__

    gateway_status = {
        "rag_service": "rag_service" in services,
        "avatar_voice_service": "avatar_voice_service" in services,
        "ai_orchestrator": ("ai_service" in services or "teacher_orchestrator" in services),
        "teacher_orchestrator": ("teacher_orchestrator" in services or "ai_service" in services),
        "ml_core_service": "ml_core_service" in services,
    }

    metrics = {
        "status": "ready",
        "port": 8005,
        "module": "backend",
        "llm_adapter": adapter_name,
        "persistence": "in_memory",
        "active_sessions_count": session_count,
        "persisted_documents_count": doc_count,
        "learner_profiles_count": profile_count,
        "gateways": gateway_status,
    }

    logger.log_telemetry_event("testbed_status_probe", metrics)
    return metrics


@app.post("/api/test/sessions", response_model=TestSessionResponse)
async def create_test_session():
    """Creates an isolated session and issues an auth token."""
    t0 = time.perf_counter()
    session_id = uuid.uuid4().hex
    token = generate_session_token()
    session_repo.create_session(session_id, token)
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    log_meta = logger.log_session_event(
        operation="create_session",
        session_id=session_id,
        input_data={"request": "POST /api/test/sessions"},
        output_data={"session_id": session_id, "token": token[:8] + "..."},
        source_function="create_test_session",
        latency_ms=latency_ms,
    )

    return TestSessionResponse(
        session_id=session_id,
        token=token,
        status="created",
        log_file=log_meta.get("log_path"),
    )


@app.post("/api/test/topic")
async def submit_test_topic(req: TestTopicRequest):
    """Submits topic and constraints for an active session."""
    t0 = time.perf_counter()
    if not session_repo.get_session_token(req.session_id):
        err = logger.log_error_event(
            operation="submit_topic",
            error_type="SessionNotFound",
            error_message=f"Session {req.session_id} does not exist",
            source_file="modules/backend/tests/web_test/server.py",
            source_function="submit_test_topic",
            input_data=req.model_dump(),
        )
        raise HTTPException(status_code=404, detail=f"Session {req.session_id} not found")

    constraints = {
        "level": req.level,
        "language": req.language,
        "time_budget_min": req.time_budget_min,
    }
    session_repo.save_topic(req.session_id, req.topic, constraints)
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    log_meta = logger.log_session_event(
        operation="save_topic_and_constraints",
        session_id=req.session_id,
        input_data={"topic": req.topic, "constraints": constraints},
        output_data={"status": "saved"},
        source_function="submit_test_topic",
        latency_ms=latency_ms,
    )

    return {
        "status": "success",
        "session_id": req.session_id,
        "topic": req.topic,
        "constraints": constraints,
        "log_file": log_meta.get("log_path"),
    }


@app.post("/api/test/upload")
async def upload_test_document(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    level: str = Form("beginner"),
    language: str = Form("en"),
    time_budget_min: int = Form(15),
):
    """Accepts document upload, saves to StorageAdapter, and relays to RAGService."""
    t0 = time.perf_counter()
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    doc_id = uuid.uuid4().hex
    safe_filename = file.filename or f"doc_{doc_id}.pdf"
    file_path = storage_adapter.put(f"{doc_id}_{safe_filename}", file_bytes)

    document_repo.create_document(
        document_id=doc_id,
        filename=safe_filename,
        mime_type=file.content_type or "application/pdf",
        file_path=file_path,
    )

    constraints = {"level": level, "language": language, "time_budget_min": time_budget_min}
    rag_service = services.get("rag_service")

    detected_structure = {"chapters": [], "key_terms": []}
    if rag_service:
        try:
            parsed_doc = rag_service.ingest_document(
                file_bytes=file_bytes,
                filename=safe_filename,
                mime_type=file.content_type or "",
                document_id=doc_id,
            )
            document_repo.update_status(doc_id, "ready")
            session_repo.save_document_context(session_id, doc_id, constraints)
            if hasattr(parsed_doc, "detected_structure"):
                detected_structure = {
                    "chapters": getattr(parsed_doc.detected_structure, "chapters", []),
                    "key_terms": getattr(parsed_doc.detected_structure, "key_terms", []),
                }
        except Exception as e:
            document_repo.update_status(doc_id, "failed", error=str(e))
            logger.log_error_event(
                operation="rag_ingest_document",
                error_type=type(e).__name__,
                error_message=str(e),
                source_file="modules/backend/tests/web_test/server.py",
                source_function="upload_test_document",
                input_data={"session_id": session_id, "filename": safe_filename},
            )
            raise HTTPException(status_code=422, detail=f"Document parsing failed: {e}")
    else:
        document_repo.update_status(doc_id, "ready")
        session_repo.save_document_context(session_id, doc_id, constraints)

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    log_meta = logger.log_rag_relay(
        session_id=session_id,
        document_id=doc_id,
        filename=safe_filename,
        file_size_bytes=len(file_bytes),
        detected_structure=detected_structure,
        source_function="upload_test_document",
        latency_ms=latency_ms,
    )

    return {
        "status": "ready",
        "document_id": doc_id,
        "filename": safe_filename,
        "size_bytes": len(file_bytes),
        "detected_structure": detected_structure,
        "log_file": log_meta.get("log_path"),
    }


@app.post("/api/test/plan")
async def generate_test_plan(req: TestPlanRequest):
    """Triggers lesson planning via SessionDriver and records state transitions."""
    t0 = time.perf_counter()
    topic_data = session_repo.get_topic_and_constraints(req.session_id)
    doc_data = session_repo.get_document_context(req.session_id)

    if not topic_data and not doc_data:
        # Pre-seed a default topic for interactive testing if none was set
        default_topic = "Newton's Laws of Motion"
        default_constraints = {"level": "beginner", "language": "en", "time_budget_min": 15}
        session_repo.save_topic(req.session_id, default_topic, default_constraints)
        topic_data = (default_topic, default_constraints)

    driver = SessionDriver(req.session_id)

    if doc_data:
        doc_id, constraints_dict = doc_data
        constraints = LearnerConstraints(**(constraints_dict or {"level": "beginner", "language": "en", "time_budget_min": 15}))
        next_state, _ = driver.step(TeacherState.UNDERSTAND, {
            "constraints": constraints,
            "topic": None,
            "document_id": doc_id,
        })
    else:
        topic, constraints_dict = topic_data
        constraints = LearnerConstraints(**(constraints_dict or {"level": "beginner", "language": "en", "time_budget_min": 15}))
        next_state, _ = driver.step(TeacherState.UNDERSTAND, {
            "constraints": constraints,
            "topic": topic,
            "document_id": None,
        })

    next_state, plan = driver.step(next_state, {})
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    plan_dict = plan.model_dump() if hasattr(plan, "model_dump") else (plan if isinstance(plan, dict) else {"lesson_id": "demo_plan"})

    if hasattr(plan, "lesson_id"):
        session_repo.save_state(req.session_id, "PLANNED", lesson_id=plan.lesson_id)
    elif isinstance(plan, dict) and "lesson_id" in plan:
        session_repo.save_state(req.session_id, "PLANNED", lesson_id=plan["lesson_id"])

    log_meta = logger.log_orchestration_step(
        session_id=req.session_id,
        current_state="UNDERSTAND",
        next_state="PLANNED",
        action="generate_lesson_plan",
        source_function="generate_test_plan",
        latency_ms=latency_ms,
        result_payload=plan_dict,
    )

    return {
        "status": "planned",
        "session_id": req.session_id,
        "lesson_plan": plan_dict,
        "log_file": log_meta.get("log_path"),
    }


@app.get("/api/test/learners/{learner_id}/profile")
async def get_test_learner_profile(learner_id: str):
    """Retrieves learner profile from in-memory repository."""
    profile = learner_repo.get_profile(learner_id)
    if not profile:
        # Generate default profile for testing
        profile = LearnerProfile(
            learner_id=learner_id,
            history=[],
            strong_concepts=["Classical Mechanics", "Newton's First Law"],
            weak_concepts=["Vector Algebra"],
            current_learning_path=["Kinematics", "Dynamics"],
            preferred_language="en",
            preferred_level="beginner",
        )
        learner_repo.save_profile(profile)

    profile_dict = profile.model_dump() if hasattr(profile, "model_dump") else profile
    return {
        "learner_id": learner_id,
        "profile": profile_dict,
    }


# -----------------------------------------------------------------------------
# Live WebSocket Simulator Endpoint
# -----------------------------------------------------------------------------

@app.websocket("/api/test/ws/{session_id}")
async def websocket_test_endpoint(websocket: WebSocket, session_id: str, token: Optional[str] = None):
    """Simulates live WebSocket bidirectional relay carrying Contract §6–11 frames."""
    await websocket.accept()

    # Log connection accept
    logger.log_websocket_frame(
        session_id=session_id,
        direction="inbound",
        event_type="connection_established",
        payload={"token_provided": bool(token)},
        state="connected",
    )

    driver = SessionDriver(session_id)

    # Reconnect/Resume check
    persisted = session_repo.get_state(session_id)
    if persisted and persisted.get("current_state") and persisted["current_state"] not in ("CREATED", "PLANNED"):
        try:
            current_state = TeacherState[persisted["current_state"]]
        except (KeyError, ValueError):
            current_state = TeacherState.EXPLAIN
    else:
        current_state = TeacherState.EXPLAIN

    # Send curriculum_loaded if plan exists
    if driver.session and driver.session.lesson_plan:
        plan_obj = driver.session.lesson_plan
        try:
            plan_dict = plan_obj.model_dump() if hasattr(plan_obj, "model_dump") else (plan_obj if isinstance(plan_obj, dict) else {})
        except Exception:
            plan_dict = {"lesson_id": "active_plan", "title": "Interactive Lesson"}

        await websocket.send_json({
            "event_type": "curriculum_loaded",
            "payload": plan_dict,
            "error": None,
        })
        logger.log_websocket_frame(
            session_id=session_id,
            direction="outbound",
            event_type="curriculum_loaded",
            payload=plan_dict,
        )

    try:
        # Dispatch initial TEACH state
        await websocket.send_json({
            "event_type": "ai_state",
            "payload": {"state": "TEACH", "concept": "Core Concepts"},
            "error": None,
        })

        # Loop receiving student responses or step triggers
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                msg = {"raw": data}

            logger.log_websocket_frame(
                session_id=session_id,
                direction="inbound",
                event_type="client_message",
                payload=msg,
            )

            client_action = msg.get("action", "")

            if client_action == "step":
                # Advance teacher state machine
                await websocket.send_json({
                    "event_type": "explanation_chunk",
                    "payload": {
                        "chunk_index": 1,
                        "text": "Energy cannot be created or destroyed; it merely changes forms.",
                        "visual_type": "diagram",
                    },
                    "error": None,
                })
                await websocket.send_json({
                    "event_type": "question_prompt",
                    "payload": {
                        "node_id": "node_1",
                        "question_text": "What happens to the total mechanical energy in a frictionless pendulum?",
                        "type": "mcq",
                        "options": ["It remains constant", "It decreases to zero", "It doubles", "It fluctuates randomly"],
                        "expected_concept": "Conservation of Energy",
                    },
                    "error": None,
                })
            elif client_action == "answer":
                # Process student answer
                student_ans = msg.get("answer", "")
                await websocket.send_json({
                    "event_type": "evaluation_result",
                    "payload": {
                        "node_id": "node_1",
                        "correct": True,
                        "partial_credit": 1.0,
                        "confidence": 0.98,
                        "feedback_text": "Spot on! The total energy remains conserved.",
                        "misconception_tag": None,
                    },
                    "error": None,
                })
            else:
                # Echo receipt
                await websocket.send_json({
                    "event_type": "ack",
                    "payload": {"status": "received", "action": client_action},
                    "error": None,
                })

    except WebSocketDisconnect:
        logger.log_websocket_frame(
            session_id=session_id,
            direction="inbound",
            event_type="websocket_disconnect",
            payload={"reason": "client_closed"},
            state="closed",
        )


# -----------------------------------------------------------------------------
# Structured Log Inspection Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/test/logs")
async def list_test_logs(
    category: Optional[str] = Query(None, description="Category filter"),
    limit: int = Query(50, ge=1, le=200, description="Max logs to return"),
):
    """Lists categorized test logs for the interactive log explorer."""
    logs = logger.list_logs(category=category, limit=limit)
    return logs


@app.get("/api/test/logs/{category}/{filename}")
async def get_log_content(category: str, filename: str):
    """Retrieves full text or JSON content of a specific log."""
    content = logger.read_log_file(category, filename)
    if content is None:
        raise HTTPException(status_code=404, detail="Log file not found")
    return {"category": category, "filename": filename, "content": content}


# -----------------------------------------------------------------------------
# Mount Static Frontend
# -----------------------------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


def main():
    import uvicorn
    port = int(os.environ.get("BACKEND_TEST_PORT", 8005))
    print("=" * 70)
    print("  SHIKSHAK AI — BACKEND MODULE ISOLATED WEB TESTBED")
    print(f"  Running on: http://localhost:{port}")
    print("  Testing Code: modules/backend/src/")
    print("  Production Backend (Port 8000) remains 100% untouched.")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
