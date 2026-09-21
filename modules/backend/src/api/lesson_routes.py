"""Lessons: creation from topic or document, planning, history, media, analytics."""
import json
import logging
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modules.backend.src.config import settings
from modules.backend.src.db.base import get_db
from modules.backend.src.db.models import Document, Lesson, User, utcnow
from modules.backend.src.deps import get_current_user
from modules.backend.src.services import lesson_service
from modules.backend.src.services.session_manager import session_manager
from modules.backend.src.security import create_ws_ticket

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lessons", tags=["lessons"])


class CreateLessonRequest(BaseModel):
    topic: Optional[str] = Field(default=None, max_length=500)
    document_id: Optional[str] = None
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    language: str = Field(default="en", max_length=10)
    time_budget_min: int = Field(default=15, ge=5, le=120)
    style: Optional[str] = Field(default=None, max_length=40)


def _owned_lesson(db: Session, lesson_id: str, user: User) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if not lesson or lesson.user_id != user.id:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    return lesson


def _owned_document(db: Session, document_id: str, user: User) -> Document:
    doc = db.get(Document, document_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------

from modules.rag.src.perf import record_memory_checkpoint

@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Store an uploaded study file and ingest it into the RAG index."""
    record_memory_checkpoint("Document upload received")
    filename = os.path.basename(file.filename or "document")
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_upload_ext:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: "
            + ", ".join(settings.allowed_upload_ext),
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(file_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is larger than {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )

    doc = Document(
        user_id=user.id,
        filename=filename,
        mime_type=file.content_type or "application/octet-stream",
        file_path="",
        size_bytes=len(file_bytes),
        status="ingesting",
    )
    db.add(doc)
    db.flush()

    # Scope uploads per user so one account can never read another's file.
    user_dir = settings.upload_root / user.id
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / f"{doc.id}{ext}"
    dest.write_bytes(file_bytes)
    doc.file_path = str(dest)
    db.flush()

    from modules.backend.src.integrations.container import services

    try:
        parsed = services["rag_service"].ingest_document(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=doc.mime_type,
            document_id=doc.id,
        )
    except Exception as exc:
        logger.exception("Ingestion failed for document %s", doc.id)
        doc.status = "failed"
        doc.error = str(exc)[:1000]
        db.flush()
        raise HTTPException(
            status_code=422,
            detail=f"We couldn't read that file: {exc}",
        ) from exc

    structure = getattr(parsed, "detected_structure", None)
    doc.status = "ready"
    doc.source_lang = getattr(parsed, "source_lang", None)
    doc.chunk_count = len(getattr(parsed, "chunks", []) or [])
    doc.chapters = list(getattr(structure, "chapters", []) or [])
    doc.key_terms = list(getattr(structure, "key_terms", []) or [])
    db.flush()

    record_memory_checkpoint("Request/response fully complete (Document Upload)")
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "size_bytes": doc.size_bytes,
        "status": doc.status,
        "source_lang": doc.source_lang,
        "chunk_count": doc.chunk_count,
        "chapters": doc.chapters,
        "key_terms": doc.key_terms,
    }


@router.get("/documents")
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.scalars(
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    ).all()
    return [
        {
            "document_id": d.id,
            "filename": d.filename,
            "size_bytes": d.size_bytes,
            "status": d.status,
            "chapters": d.chapters,
            "key_terms": d.key_terms,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    doc = _owned_document(db, document_id, user)
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(doc)
    db.flush()
    return {"status": "ok", "message": "Document deleted."}


# --------------------------------------------------------------------------
# Lessons
# --------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
def create_lesson(
    payload: CreateLessonRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a lesson from a topic or an already-ingested document."""
    topic = (payload.topic or "").strip()
    if not topic and not payload.document_id:
        raise HTTPException(
            status_code=422, detail="Provide a topic or choose an uploaded document."
        )

    document = None
    if payload.document_id:
        document = _owned_document(db, payload.document_id, user)
        if document.status != "ready":
            raise HTTPException(
                status_code=409,
                detail=f"That document is not ready yet (status: {document.status}).",
            )

    lesson = Lesson(
        user_id=user.id,
        title=topic or (document.filename if document else "Lesson"),
        source="document" if document else "topic",
        topic=topic or None,
        document_id=document.id if document else None,
        level=payload.level,
        language=payload.language,
        time_budget_min=payload.time_budget_min,
        style=payload.style,
        status="created",
    )
    db.add(lesson)
    db.flush()
    lesson_service.log_event(db, lesson, "lesson_created")

    return {"lesson_id": lesson.id, "status": lesson.status, "title": lesson.title}


@router.post("/{lesson_id}/plan")
def generate_plan(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run UNDERSTAND + PLAN and persist the resulting curriculum."""
    lesson = _owned_lesson(db, lesson_id, user)

    if lesson.plan_json and lesson.status not in ("created",):
        return {"lesson_id": lesson.id, "plan": lesson.plan_json, "regenerated": False}

    try:
        plan = session_manager.build_plan(lesson, db)
    except Exception as exc:
        logger.exception("Planning failed for lesson %s", lesson.id)
        raise HTTPException(
            status_code=502, detail=f"The lesson planner could not build a plan: {exc}"
        ) from exc

    lesson_service.persist_plan(db, lesson, plan)
    db.flush()

    return {
        "lesson_id": lesson.id,
        "plan": lesson.plan_json,
        "regenerated": True,
        "detail": lesson_service.lesson_detail(db, lesson),
    }


@router.post("/{lesson_id}/ticket")
def issue_ws_ticket(
    lesson_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mint a short-lived ticket for the live classroom WebSocket.

    Access tokens never go in a URL, because URLs leak via logs and Referer.
    """
    lesson = _owned_lesson(db, lesson_id, user)
    if not lesson.plan_json:
        raise HTTPException(status_code=409, detail="Generate the lesson plan first.")
    return {
        "ticket": create_ws_ticket(user.id, lesson.id),
        "expires_in": settings.ws_ticket_ttl_sec,
        "ws_path": f"{settings.api_v1_str}/lessons/{lesson.id}/live",
    }


@router.get("")
def list_lessons(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    query = select(Lesson).where(Lesson.user_id == user.id)
    if status_filter and status_filter != "all":
        query = query.where(Lesson.status == status_filter)
    if search:
        query = query.where(Lesson.title.ilike(f"%{search.strip()}%"))

    total = db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0
    rows = db.scalars(
        query.order_by(Lesson.updated_at.desc()).limit(limit).offset(offset)
    ).all()

    return {
        "lessons": [lesson_service.lesson_summary(db, lesson) for lesson in rows],
        "count": len(rows),
        "total": total,
        "offset": offset,
        "has_more": offset + len(rows) < total,
    }


@router.get("/{lesson_id}")
def get_lesson(
    lesson_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    lesson = _owned_lesson(db, lesson_id, user)
    return lesson_service.lesson_detail(db, lesson)


@router.delete("/{lesson_id}")
def delete_lesson(
    lesson_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    lesson = _owned_lesson(db, lesson_id, user)
    media_dir = settings.media_root / lesson.id
    db.delete(lesson)
    db.flush()
    try:
        if media_dir.exists():
            for child in media_dir.iterdir():
                child.unlink(missing_ok=True)
            media_dir.rmdir()
    except OSError:
        pass
    lesson_service.refresh_learner_profile(db, user.id)
    return {"status": "ok", "message": "Lesson deleted."}


# --------------------------------------------------------------------------
# Media — served only to the lesson's owner, never by arbitrary path
# --------------------------------------------------------------------------

def _serve_owned_media(stored_path: Optional[str], lesson_id: str, media_type: str) -> FileResponse:
    if not stored_path:
        raise HTTPException(status_code=404, detail="No media for this node yet.")

    path = Path(stored_path).resolve()
    root = settings.media_root.resolve()
    # Containment check: a stored path must live under this lesson's media dir.
    try:
        path.relative_to(root / lesson_id)
    except ValueError:
        logger.error("Blocked out-of-root media access: %s", path)
        raise HTTPException(status_code=404, detail="Media not found.")

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Media file is no longer available.")
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/{lesson_id}/notes")
def get_lesson_notes(
    lesson_id: str,
    format: Literal["json", "markdown"] = Query("json"),
    download: bool = Query(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The lesson's chapter notes — as JSON for the UI, or a Markdown study sheet."""
    lesson = _owned_lesson(db, lesson_id, user)

    if format == "markdown":
        markdown = lesson_service.lesson_notes_markdown(db, lesson)
        headers = {}
        if download:
            safe = "".join(
                ch if ch.isalnum() or ch in " -_" else "" for ch in (lesson.title or "lesson")
            ).strip() or "lesson"
            headers["Content-Disposition"] = f'attachment; filename="{safe[:80]} - notes.md"'
        return Response(
            content=markdown, media_type="text/markdown; charset=utf-8", headers=headers
        )

    nodes = sorted(lesson.nodes, key=lambda n: n.position)
    return {
        "lesson_id": lesson.id,
        "title": lesson.title,
        "notes": [
            {
                "node_id": n.node_id,
                "concept": n.concept,
                "depth": n.depth,
                "est_minutes": n.est_minutes,
                "status": n.status,
                "key_points": (n.notes_json or {}).get("key_points") or [],
                "example": (n.notes_json or {}).get("example"),
                "script_text": n.script_text,
                "citation": n.citation_json,
            }
            for n in nodes
            if n.script_text or n.notes_json
        ],
    }


@router.get("/{lesson_id}/nodes/{node_id}/video")
def get_node_video(
    lesson_id: str,
    node_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = _owned_lesson(db, lesson_id, user)
    node = lesson_service.get_node(db, lesson, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found.")
    return _serve_owned_media(node.video_path, lesson.id, "video/mp4")


@router.get("/{lesson_id}/nodes/{node_id}/captions")
def get_node_captions(
    lesson_id: str,
    node_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = _owned_lesson(db, lesson_id, user)
    node = lesson_service.get_node(db, lesson, node_id)
    if not node or not node.captions_url:
        raise HTTPException(status_code=404, detail="No captions for this node.")
    caption_path = settings.media_root / lesson.id
    matches = list(caption_path.glob(f"{node_id}_*.vtt"))
    if not matches:
        raise HTTPException(status_code=404, detail="Captions file is no longer available.")
    return _serve_owned_media(str(matches[0]), lesson.id, "text/vtt")
