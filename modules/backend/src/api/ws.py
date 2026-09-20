"""Live classroom WebSocket: drives the teaching FSM and persists every step."""
import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.backend.src.db.base import SessionLocal
from modules.backend.src.db.models import Interaction, Lesson, User, utcnow
from modules.backend.src.schemas.contract import StudentResponse
from modules.backend.src.schemas.ws import WSMessage
from modules.backend.src.security import decode_token
from modules.backend.src.services import lesson_service
from modules.backend.src.services.session_manager import session_manager

logger = logging.getLogger(__name__)
router = APIRouter()

RENDER_POLL_SEC = 0.4
RENDER_TIMEOUT_SEC = 420


def _as_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return dict(obj)


class LiveSession:
    """Owns one learner's socket, its DB session, and the FSM loop."""

    def __init__(self, websocket: WebSocket, lesson_id: str, user_id: str):
        self.ws = websocket
        self.lesson_id = lesson_id
        self.user_id = user_id
        self.db: Session = SessionLocal()
        self.lesson: Optional[Lesson] = None
        self.pending_interaction: Optional[Interaction] = None

    # -- plumbing ------------------------------------------------------------

    def close_db(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Failed to commit lesson progress for %s", self.lesson_id)

    async def send(self, event_type: str, payload: Any = None, error: Optional[str] = None) -> None:
        await self.ws.send_json(
            WSMessage(event_type=event_type, payload=payload or {}, error=error).model_dump()
        )

    def _run(self, fn, *args, **kwargs):
        """Run blocking work (LLM calls, rendering, DB) off the event loop."""
        return asyncio.get_running_loop().run_in_executor(None, lambda: fn(*args, **kwargs))

    # -- lifecycle -----------------------------------------------------------

    def load_lesson(self) -> bool:
        lesson = self.db.get(Lesson, self.lesson_id)
        if not lesson or lesson.user_id != self.user_id:
            return False
        self.lesson = lesson
        return True

    async def run(self) -> None:
        lesson = self.lesson
        assert lesson is not None

        await self.send(
            "session_ready",
            {
                "lesson_id": lesson.id,
                "title": lesson.title,
                "status": lesson.status,
                "resumed": lesson.status == "in_progress",
                "current_node_index": lesson.current_node_index,
            },
        )

        if lesson.plan_json:
            await self.send("curriculum_loaded", lesson.plan_json)
            await self.send("progress_snapshot", self._progress_snapshot())

        state = session_manager.resume_state(lesson)

        while True:
            lesson.fsm_state = state.name
            self.commit()

            if state == TeacherState.PLAN:
                state = await self._do_plan(state)
            elif state == TeacherState.EXPLAIN:
                state = await self._do_explain(state)
            elif state == TeacherState.QUESTION:
                state = await self._do_question(state)
            elif state == TeacherState.CONTINUE:
                state = await self._do_continue(state)
            elif state == TeacherState.DONE:
                await self._do_done(state)
                break
            elif state == TeacherState.HUMAN_ESCALATION:
                await self._do_escalation()
                break
            else:
                logger.warning("Unexpected FSM state %s in live session", state)
                break

    # -- FSM steps -----------------------------------------------------------

    async def _do_plan(self, state: TeacherState) -> TeacherState:
        await self.send("ai_state", {"state": "PLAN"})
        # A mid-lesson re-plan must stay grounded in the same document.
        outline = session_manager.outline_for(self.lesson, self.db)
        if outline:
            session_manager.get_or_restore(self.lesson).document_outline = outline
        next_state, plan = await self._run(session_manager.step, self.lesson, state, {})
        lesson_service.persist_plan(self.db, self.lesson, plan)
        self.commit()
        await self.send("lesson_plan_update", self.lesson.plan_json)
        await self.send("progress_snapshot", self._progress_snapshot())
        return next_state

    async def _do_explain(self, state: TeacherState) -> TeacherState:
        node = session_manager.current_node(self.lesson)
        if node is None:
            return TeacherState.DONE

        await self.send("ai_state", {"state": "TEACH", "node_id": node.node_id, "concept": node.concept})

        next_state, segment = await self._run(session_manager.step, self.lesson, state, {})
        script_text = getattr(segment, "script_text", "") or ""

        lesson_service.mark_node_teaching(self.db, self.lesson, node.node_id, script_text)
        self.commit()

        await self.send(
            "explanation_chunk",
            {
                "node_id": node.node_id,
                "concept": node.concept,
                "title": node.concept,
                "script_text": script_text,
                "visual_spec": _as_dict(getattr(segment, "visual_spec", None)),
                "avatar_cue": getattr(segment, "avatar_cue", "neutral"),
            },
        )

        if self.lesson.document_id:
            # TeachingSegment has no grounding field, so the passages come from
            # the orchestrator session that retrieved them.
            chunks = session_manager.current_grounding(self.lesson)
            if chunks:
                citation = {
                    "source_title": self.lesson.title,
                    "excerpt": chunks[0] if isinstance(chunks[0], str) else str(chunks[0]),
                    "node_id": node.node_id,
                }
                lesson_service.record_citation(self.db, self.lesson, node.node_id, citation)
                self.commit()
                await self.send("citation_updated", citation)

        # DEMONSTRATE enqueues the render and tells us whether a question follows.
        next_state, payload = await self._run(
            session_manager.step, self.lesson, next_state, {"segment": segment}
        )
        job_id = payload.get("job_id") if isinstance(payload, dict) else None

        if job_id:
            await self.send("render_started", {"node_id": node.node_id, "job_id": job_id})
            await self._await_render(job_id, node, script_text)

        return next_state

    async def _await_render(self, job_id: str, node: Any, script_text: str) -> None:
        from modules.backend.src.integrations.container import services

        avatar = services["avatar_voice_service"]
        waited = 0.0

        while waited < RENDER_TIMEOUT_SEC:
            status = await self._run(avatar.get_status, job_id)

            if status and status.status == "done":
                result = _as_dict(status.result)
                video_path = result.get("video_url") or ""
                captions = result.get("captions_vtt_url")
                duration = float(result.get("duration_sec") or 0.0)

                served_url = lesson_service.attach_media(
                    self.db, self.lesson, node.node_id, video_path, duration, captions
                )
                self.commit()

                await self.send(
                    "video_segment",
                    {
                        "node_id": node.node_id,
                        "title": node.concept,
                        "script_text": script_text,
                        "video_url": served_url,
                        "captions_url": lesson_service.get_node(
                            self.db, self.lesson, node.node_id
                        ).captions_url,
                        "duration_sec": duration,
                    },
                )
                return

            if status and status.status == "failed":
                logger.error("Render job %s failed: %s", job_id, status.error)
                # Teaching continues with the script on the board rather than
                # dead-ending the whole lesson on one failed render.
                await self.send(
                    "render_failed",
                    {"node_id": node.node_id, "reason": status.error or "Rendering failed"},
                )
                return

            await asyncio.sleep(RENDER_POLL_SEC)
            waited += RENDER_POLL_SEC

        await self.send(
            "render_failed",
            {"node_id": node.node_id, "reason": "Rendering timed out. Continuing with the text explanation."},
        )

    async def _do_question(self, state: TeacherState) -> TeacherState:
        await self.send("ai_state", {"state": "INTERACT"})

        next_state, question = await self._run(session_manager.step, self.lesson, state, {})
        interaction = lesson_service.record_question(self.db, self.lesson, question)
        self.pending_interaction = interaction
        self.commit()

        q = _as_dict(question)
        await self.send(
            "interaction_event",
            {
                "interaction_id": interaction.id,
                "node_id": q.get("node_id"),
                "question_text": q.get("question_text"),
                "type": q.get("type"),
                "options": q.get("options") or [],
            },
        )

        # Wait for the learner. Anything that isn't an answer is handled and re-awaited.
        while True:
            data = await self.ws.receive_json()
            message = WSMessage(**data)

            if message.event_type == "student_response":
                break
            if message.event_type == "ping":
                await self.send("pong", {})
                continue
            if message.event_type == "reaction":
                lesson_service.log_event(
                    self.db, self.lesson, "reaction", payload=message.payload
                )
                self.commit()
                continue
            await self.send("error", {}, error=f"Unexpected event '{message.event_type}'.")

        payload = message.payload or {}
        raw_answer = str(payload.get("raw_answer", "")).strip()
        if not raw_answer:
            await self.send("error", {}, error="Your answer was empty.")
            return TeacherState.QUESTION

        # The client's claimed type is ignored; the orchestrator grades using the
        # type of the question it actually asked.
        response = StudentResponse(
            node_id=interaction.node_id,
            raw_answer=raw_answer,
            response_type=interaction.question_type,
            response_time_sec=float(payload.get("response_time_sec") or 0.0),
        )
        lesson_service.record_answer(self.db, interaction, raw_answer, response.response_time_sec)
        self.commit()

        await self.send("ai_state", {"state": "EVALUATE"})
        next_state, evaluation = await self._run(
            session_manager.step, self.lesson, TeacherState.EVALUATE, {"student_response": response}
        )
        lesson_service.record_evaluation(self.db, self.lesson, interaction, evaluation)
        self.commit()
        await self.send("evaluation_result", _as_dict(evaluation))

        next_state, decision = await self._run(
            session_manager.step, self.lesson, next_state, {"eval_result": evaluation}
        )
        lesson_service.record_adaptation(self.db, self.lesson, interaction, decision)
        self.commit()

        await self.send("adaptation_decision", _as_dict(decision))
        await self.send("progress_snapshot", self._progress_snapshot())
        self.pending_interaction = None
        return next_state

    async def _do_continue(self, state: TeacherState) -> TeacherState:
        next_state, _ = await self._run(session_manager.step, self.lesson, state, {})
        index = session_manager.sync_index(self.lesson)
        lesson_service.advance_node(self.db, self.lesson, index)
        self.commit()
        await self.send("progress_snapshot", self._progress_snapshot())
        return next_state

    async def _do_done(self, state: TeacherState) -> None:
        await self.send("ai_state", {"state": "ASSESS"})
        _, report = await self._run(session_manager.step, self.lesson, state, {})
        row = lesson_service.complete_lesson(self.db, self.lesson, report)
        self.commit()

        await self.send(
            "assessment_report",
            {
                "lesson_id": self.lesson.id,
                "score_pct": row.score_pct,
                "strong_areas": row.strong_areas,
                "weak_areas": row.weak_areas,
                "recommended_next": row.recommended_next,
                "narrative_feedback": row.narrative_feedback,
                "report_url": f"/report.html?lesson={self.lesson.id}",
            },
        )
        session_manager.reset(self.lesson.id)

    async def _do_escalation(self) -> None:
        self.lesson.status = "escalated"
        self.lesson.fsm_state = "HUMAN_ESCALATION"
        lesson_service.log_event(self.db, self.lesson, "human_escalation")
        lesson_service.refresh_learner_profile(self.db, self.user_id)
        self.commit()
        await self.send(
            "human_escalation",
            {
                "reason": "This concept needs a human teacher — the same misconception "
                "persisted across several attempts.",
                "lesson_id": self.lesson.id,
            },
        )

    # -- helpers -------------------------------------------------------------

    def _progress_snapshot(self) -> dict:
        self.db.refresh(self.lesson)
        nodes = sorted(self.lesson.nodes, key=lambda n: n.position)
        done = sum(1 for n in nodes if n.status in ("mastered", "skipped"))
        return {
            "lesson_id": self.lesson.id,
            "status": self.lesson.status,
            "current_node_index": self.lesson.current_node_index,
            "nodes_completed": done,
            "node_count": len(nodes),
            "progress_pct": round(100.0 * done / len(nodes), 1) if nodes else 0.0,
            "watch_minutes": round((self.lesson.total_watch_sec or 0) / 60.0, 1),
            "nodes": [
                {
                    "node_id": n.node_id,
                    "concept": n.concept,
                    "status": n.status,
                    "mastery_score": round(n.mastery_score, 2),
                    "attempts": n.attempts,
                    "checkpoint_question": n.checkpoint_question,
                    "video_url": n.video_url,
                }
                for n in nodes
            ],
        }


@router.websocket("/lessons/{lesson_id}/live")
async def live_classroom(
    websocket: WebSocket,
    lesson_id: str,
    ticket: str = Query(..., description="Short-lived WS ticket from POST /lessons/{id}/ticket"),
):
    await websocket.accept()

    payload = decode_token(ticket, expected_type="ws_ticket")
    if not payload or payload.get("lesson_id") != lesson_id:
        await websocket.send_json(
            WSMessage(
                event_type="error", payload={}, error="Invalid or expired session ticket."
            ).model_dump()
        )
        await websocket.close(code=1008)
        return

    session = LiveSession(websocket, lesson_id, payload["sub"])

    try:
        user = session.db.get(User, payload["sub"])
        if not user or not user.is_active or not user.is_verified:
            await session.send("error", {}, error="Your account is not authorised.")
            await websocket.close(code=1008)
            return

        if not session.load_lesson():
            await session.send("error", {}, error="Lesson not found.")
            await websocket.close(code=1008)
            return

        await session.run()

    except WebSocketDisconnect:
        logger.info("Learner disconnected from lesson %s; progress is saved", lesson_id)
        if session.lesson and session.lesson.status == "in_progress":
            lesson_service.log_event(session.db, session.lesson, "disconnected")
            session.commit()
    except Exception as exc:
        logger.exception("Live classroom error for lesson %s", lesson_id)
        try:
            await session.send("error", {}, error=f"The lesson hit an error: {exc}")
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        session.close_db()
