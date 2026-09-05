import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from modules.backend.src.auth import generate_session_token, get_token_header
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
from modules.backend.src.state.driver import SessionDriver
from modules.backend.src.integrations.container import services
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState

router = APIRouter()


class SessionResponse(BaseModel):
    session_id: str
    token: str


@router.post("/sessions", response_model=SessionResponse)
async def create_session():
    session_id = uuid.uuid4().hex
    token = generate_session_token()
    session_repo.create_session(session_id, token)
    return SessionResponse(session_id=session_id, token=token)


@router.post("/sessions/{session_id}/topic")
async def submit_topic(
    session_id: str,
    request: TopicRequest,
    token: str = Depends(get_token_header),
):
    if session_repo.get_session_token(session_id) != token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_repo.save_topic(session_id, request.topic, request.constraints.model_dump())
    return {"status": "success"}


@router.post("/sessions/{session_id}/upload")
async def upload_document(
    session_id: str,
    file: UploadFile = File(...),
    constraints: Optional[str] = Form(None),
    token: str = Depends(get_token_header),
):
    """Accepts multipart document upload, saves bytes to StorageAdapter, and ingests via RAGService."""
    if session_repo.get_session_token(session_id) != token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    parsed_constraints = None
    if constraints:
        try:
            parsed_constraints = json.loads(constraints)
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid constraints JSON format")

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

    rag_service = services["rag_service"]
    try:
        parsed_doc = rag_service.ingest_document(
            file_bytes=file_bytes,
            filename=safe_filename,
            mime_type=file.content_type or "",
            document_id=doc_id,
        )
        document_repo.update_status(doc_id, "ready")
        session_repo.save_document_context(session_id, doc_id, parsed_constraints)
        return {
            "status": "ready",
            "document_id": doc_id,
            "detected_structure": {
                "chapters": parsed_doc.detected_structure.chapters,
                "key_terms": parsed_doc.detected_structure.key_terms,
            },
        }
    except Exception as e:
        document_repo.update_status(doc_id, "failed", error=str(e))
        raise HTTPException(status_code=422, detail=f"Document parsing failed: {e}")


@router.post("/sessions/{session_id}/plan", response_model=LessonPlan)
async def generate_plan(
    session_id: str,
    token: str = Depends(get_token_header),
):
    if session_repo.get_session_token(session_id) != token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    topic_data = session_repo.get_topic_and_constraints(session_id)
    doc_data = session_repo.get_document_context(session_id)

    if not topic_data and not doc_data:
        raise HTTPException(status_code=400, detail="Neither topic nor document uploaded yet")

    driver = SessionDriver(session_id)

    if doc_data:
        doc_id, constraints_dict = doc_data
        constraints_dict = constraints_dict or {"level": "beginner", "language": "en", "time_budget_min": 15}
        constraints = LearnerConstraints(**constraints_dict)
        next_state, _ = driver.step(TeacherState.UNDERSTAND, {
            "constraints": constraints,
            "topic": None,
            "document_id": doc_id,
        })
    else:
        topic, constraints_dict = topic_data
        constraints = LearnerConstraints(**constraints_dict)
        next_state, _ = driver.step(TeacherState.UNDERSTAND, {
            "constraints": constraints,
            "topic": topic,
            "document_id": None,
        })

    next_state, plan = driver.step(next_state, {})

    # Record state checkpoint
    if hasattr(plan, "lesson_id"):
        session_repo.save_state(session_id, "PLANNED", lesson_id=plan.lesson_id)
    elif isinstance(plan, dict) and "lesson_id" in plan:
        session_repo.save_state(session_id, "PLANNED", lesson_id=plan["lesson_id"])

    return plan


@router.get("/learners/{learner_id}/profile", response_model=LearnerProfile)
async def get_learner_profile(
    learner_id: str,
    token: str = Depends(get_token_header),
):
    """Retrieve learner profile (Contract §13)."""
    profile = learner_repo.get_profile(learner_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Learner profile not found")
    return profile


@router.get("/learners/{learner_id}/report/{lesson_id}", response_model=AssessmentReport)
async def get_assessment_report(
    learner_id: str,
    lesson_id: str,
    token: str = Depends(get_token_header),
):
    """Retrieve assessment report for a completed lesson (Contract §12)."""
    report = report_repo.get_report(learner_id, lesson_id)
    if not report:
        raise HTTPException(status_code=404, detail="Assessment report not found")
    return report


@router.get("/sessions/{session_id}/plan", response_model=LessonPlan)
async def get_plan(
    session_id: str,
    token: str = Depends(get_token_header),
):
    if session_repo.get_session_token(session_id) != token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        driver = SessionDriver(session_id)
        if driver.session and driver.session.lesson_plan:
            return driver.session.lesson_plan
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Plan not found for this session")


from fastapi.responses import FileResponse
import os

@router.get("/media/video")
async def get_rendered_video(path: Optional[str] = None, file: Optional[str] = None):
    """Safely stream rendered video files to the frontend."""
    target_path = path or file
    if not target_path or not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(target_path, media_type="video/mp4")

