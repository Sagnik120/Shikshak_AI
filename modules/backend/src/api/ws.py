"""Live classroom WebSocket: drives the teaching FSM and persists every step.

Teaching flow per concept
-------------------------
Explain (script) -> render the video while the checkpoint questions are
written -> the video plays and PAUSES at each checkpoint; the learner answers a
question about what has been covered so far:

* right (or close enough)  -> ALLOW: the video resumes
* wrong                    -> MODIFY: the concept is re-explained differently
* wrong again on it        -> REGENERATE: this segment is rebuilt from scratch
* > 3 wrong in the lesson  -> HUMAN: the lesson stops for a human teacher

When the video ends with every checkpoint passed, the lesson moves on.

Transport
---------
A reader task drains the socket continuously. uvicorn stops reading a socket
after each message until the app receives it, so a heartbeat arriving while
the server was busy rendering left the browser's keepalive pong unread and
the server dropped the connection 20 s later. Drops still happen on real
networks, so: one driver per lesson (a new connection takes over), and
resume replays saved material instead of regenerating it.
"""
import asyncio
import json
import time
import logging
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from modules.ai_agent_orchestration.src.state_machine.orchestrator import REGENERATE_BRIEF
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.backend.src.config import settings
from modules.backend.src.db.base import SessionLocal
from modules.backend.src.db.models import Interaction, Lesson, User
from modules.backend.src.schemas.contract import StudentResponse
from modules.backend.src.schemas.ws import WSMessage
from modules.backend.src.security import decode_token
from modules.backend.src.services import escalation_service, lesson_service
from modules.backend.src.services.email_service import email_service
from modules.backend.src.services.session_manager import session_manager

logger = logging.getLogger(__name__)
router = APIRouter()

RENDER_POLL_SEC = 0.4
RENDER_TIMEOUT_SEC = 420
# Close code telling a browser tab that another connection took this lesson
# over, so it must not auto-reconnect and fight for it.
SUPERSEDED_CLOSE_CODE = 4001
# How long a new connection waits for the previous driver to finish its
# in-flight step (at most one LLM call) before taking over anyway.
PREVIOUS_DRIVER_WAIT_SEC = 120

_ACTIVE: dict[str, "LiveSession"] = {}

_ADAPT_NEXT = {
    "MODIFY": TeacherState.EXPLAIN,
    "REGENERATE": TeacherState.EXPLAIN,
    "HUMAN": TeacherState.HUMAN_ESCALATION,
}

_VTT_TIME = re.compile(r"(\d+):(\d+):(\d+)\.(\d+)\s+-->\s+(\d+):(\d+):(\d+)\.(\d+)")


def _as_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return dict(obj)


def _word_end_times(captions_path: Optional[str]) -> list[float]:
    """End time of each spoken word, from the word-level captions file."""
    try:
        text = Path(captions_path).read_text(encoding="utf-8") if captions_path else ""
    except OSError:
        return []
    ends = []
    for m in _VTT_TIME.finditer(text):
        h, mnt, s, ms = int(m[5]), int(m[6]), int(m[7]), m[8]
        ends.append(h * 3600 + mnt * 60 + s + int(ms) / (10 ** len(ms)))
    return ends


def _checkpoint_time(word: int, total_words: int, duration: float, ends: list[float]) -> float:
    if ends and total_words:
        i = min(len(ends) - 1, max(0, round(word * len(ends) / total_words) - 1))
        return round(ends[i] + 0.3, 2)  # just after the sentence is spoken
    return round(duration * word / max(total_words, 1), 2)


# One lock per (lesson, node): the live classroom and the background finisher
# may both see the same render finish; only one of them attaches it.
_ATTACH_LOCKS: dict[tuple, asyncio.Lock] = {}
_FINISHERS: set = set()


def _fill_checkpoint_times(db: Session, lesson: Lesson, node_id: str, script: str, media: dict) -> None:
    row = lesson_service.get_node(db, lesson, node_id)
    # Copies: mutating the stored dicts in place would also change SQLAlchemy's
    # snapshot of the old value, so the update would never be written.
    items = [dict(it) for it in ((row.checkpoints_json if row else None) or {}).get("items") or []]
    if not items or all(it.get("at_sec") is not None for it in items):
        return
    ends = _word_end_times(media.get("captions_path"))
    total = len(script.split())
    for it in items:
        it["at_sec"] = _checkpoint_time(it["word"], total, media["duration"], ends)
    data = dict(row.checkpoints_json)
    data["items"] = items
    row.checkpoints_json = data  # keep issued_at: answered checkpoints still count
    db.flush()


async def _attach_once(db: Session, lesson: Lesson, node_id: str, script: str, result: dict) -> Optional[dict]:
    """Attach a finished render to its node exactly once. None if the node has
    moved on to a different explanation since (the render is stale)."""
    lock = _ATTACH_LOCKS.setdefault((lesson.id, node_id), asyncio.Lock())
    async with lock:
        db.expire_all()
        row = lesson_service.get_node(db, lesson, node_id)
        if row is None or (row.script_text or "") != script:
            return None
        duration = float(result.get("duration_sec") or 0.0)
        captions_path = result.get("captions_vtt_url")
        if not row.video_url:
            lesson_service.attach_media(db, lesson, node_id, result.get("video_url") or "", duration, captions_path)
        media = {"video_url": row.video_url, "captions_url": row.captions_url,
                 "duration": row.duration_sec or duration, "captions_path": captions_path}
        _fill_checkpoint_times(db, lesson, node_id, script, media)
        db.commit()
        return media


async def _finish_render_later(lesson_id: str, node_id: str, job_id: str, script: str) -> None:
    """The learner left mid-render: finish and save the video anyway, so it is
    ready the moment they come back (and is never rendered twice)."""
    from modules.backend.src.integrations.container import services

    avatar = services["avatar_voice_service"]
    loop = asyncio.get_running_loop()
    waited, status = 0.0, None
    while waited < RENDER_TIMEOUT_SEC:
        status = await loop.run_in_executor(None, avatar.get_status, job_id)
        if status and status.status in ("done", "failed"):
            break
        await asyncio.sleep(1.0)
        waited += 1.0
    if not status or status.status != "done":
        return
    db = SessionLocal()
    try:
        lesson = db.get(Lesson, lesson_id)
        if lesson is not None and await _attach_once(db, lesson, node_id, script, _as_dict(status.result)):
            logger.info("Saved the %s video for lesson %s after the learner left", node_id, lesson_id)
    except Exception:
        logger.exception("Background render save failed for %s/%s", lesson_id, node_id)
        db.rollback()
    finally:
        db.close()
        _FINISHERS.discard(job_id)


def _finish_in_background(lesson_id: str, node_id: str, job_id: str, script: str) -> None:
    if job_id in _FINISHERS:
        return
    _FINISHERS.add(job_id)
    asyncio.get_running_loop().create_task(_finish_render_later(lesson_id, node_id, job_id, script))


async def stop_active(lesson_id: str) -> None:
    """Stop any live classroom on this lesson (after it saves its step), so an
    action from another page can change the lesson safely."""
    active = _ACTIVE.get(lesson_id)
    if active is not None and not active.done.is_set():
        await active.supersede()
        try:
            await asyncio.wait_for(active.done.wait(), PREVIOUS_DRIVER_WAIT_SEC)
        except asyncio.TimeoutError:
            logger.warning("Live classroom for %s did not stop in time", lesson_id)


class LiveSession:
    """Owns one learner's socket, its DB session, and the FSM loop."""

    def __init__(self, websocket: WebSocket, lesson_id: str, user_id: str):
        self.ws = websocket
        self.lesson_id = lesson_id
        self.user_id = user_id
        self.db: Session = SessionLocal()
        self.lesson: Optional[Lesson] = None
        # False once the socket is gone or a newer connection took over: the
        # loop then finishes (and saves) its current step and stops.
        self.alive = True
        self.done = asyncio.Event()
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.connected_at = time.time()  # for the admin "live classrooms" view
        self._reader_task: Optional[asyncio.Task] = None

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
        if not self.alive:
            return
        try:
            await self.ws.send_json(
                WSMessage(event_type=event_type, payload=payload or {}, error=error).model_dump()
            )
        except Exception:
            # The socket is gone. Keep going so the current step's result is
            # still saved for the reconnect; the loop stops at the next step.
            self.alive = False

    def start_reader(self) -> None:
        self._reader_task = asyncio.create_task(self._reader())

    async def _reader(self) -> None:
        """Drain the socket continuously (see module docstring)."""
        try:
            while True:
                raw = await self.ws.receive_text()
                try:
                    message = WSMessage(**json.loads(raw))
                except Exception:
                    continue  # malformed frames are ignored, not fatal
                if message.event_type == "ping":
                    await self.send("pong", {})
                    continue
                await self.inbox.put(message)
        except Exception:
            pass
        finally:
            self.alive = False
            await self.inbox.put(None)

    async def next_message(self) -> WSMessage:
        message = await self.inbox.get()
        if message is None:
            self.inbox.put_nowait(None)  # every later wait sees the end too
            raise WebSocketDisconnect(code=1001)
        return message

    async def supersede(self) -> None:
        self.alive = False
        try:
            await self.ws.close(code=SUPERSEDED_CLOSE_CODE)
        except Exception:
            pass

    def stop_reader(self) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()

    def _run(self, fn, *args, **kwargs):
        """Run blocking work (LLM calls, rendering, DB) off the event loop."""
        return asyncio.get_running_loop().run_in_executor(None, lambda: fn(*args, **kwargs))

    def _log_reaction(self, message: WSMessage) -> None:
        lesson_service.log_event(self.db, self.lesson, "reaction", payload=message.payload)
        self.commit()

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

        state = await self._resume()

        while self.alive and state is not None:
            lesson.fsm_state = state.name
            self.commit()

            if state == TeacherState.PLAN:
                state = await self._do_plan(state)
            elif state == TeacherState.EXPLAIN:
                state = await self._do_explain(state)
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

    # -- resume --------------------------------------------------------------

    async def _resume(self) -> Optional[TeacherState]:
        """Pick up exactly where the learner was, reusing everything saved."""
        lesson = self.lesson
        state = session_manager.resume_state(lesson)
        if lesson.status != "in_progress" or state != TeacherState.EXPLAIN:
            return state

        node = session_manager.current_node(lesson)
        row = lesson_service.get_node(self.db, lesson, node.node_id) if node else None
        if row is None:
            return state

        latest = lesson_service.latest_interaction(self.db, lesson, node.node_id)
        fsm = lesson.fsm_state

        # Graded, but the (rule-based, instant) adaptation never ran.
        if fsm == "EVALUATE" and latest is not None and latest.correct is not None:
            evaluation = {
                "node_id": latest.node_id,
                "correct": bool(latest.correct),
                "partial_credit": latest.partial_credit,
                "misconception_tag": latest.misconception_tag,
                "confidence": min(1.0, max(0.0, latest.confidence or 0.0)),
                "feedback_text": latest.feedback_text or "",
            }
            await self.send("evaluation_result", evaluation)
            outcome = await self._adapt(latest, evaluation)
            if outcome is not None:
                return outcome
            fsm = "ADAPT"  # allowed: carry on with the same video below

        # A decision to re-teach was made; only the re-teaching is left.
        if fsm == "ADAPT" and latest is not None and latest.adaptation_action in _ADAPT_NEXT:
            session = session_manager.get_or_restore(lesson)
            if latest.adaptation_action == "MODIFY":
                session.current_feedback_override = latest.adaptation_reason
            elif latest.adaptation_action == "REGENERATE":
                session.current_feedback_override = REGENERATE_BRIEF
            return _ADAPT_NEXT[latest.adaptation_action]

        if row.status in lesson_service.DONE_STATUSES:
            return TeacherState.CONTINUE
        if not row.script_text:
            return TeacherState.EXPLAIN  # the explanation itself never finished

        logger.info("Resuming lesson %s at %s from saved material", lesson.id, node.node_id)
        segment = session_manager.restore_segment(lesson, row)
        await self._send_explanation(node, segment, replay=True)
        if row.citation_json:
            await self.send("citation_updated", row.citation_json)

        checkpoints = row.checkpoints_json
        if not checkpoints:
            checkpoints = await self._make_checkpoints(node, segment)
        return await self._deliver_and_teach(node, row, segment, checkpoints, replay=True)

    # -- FSM steps -----------------------------------------------------------

    async def _do_plan(self, state: TeacherState) -> TeacherState:
        await self.send("ai_state", {"state": "PLAN"})
        outline = session_manager.outline_for(self.lesson, self.db)
        session = session_manager.get_or_restore(self.lesson)
        if outline:
            session.document_outline = outline
        session.learner_profile = session_manager.memory_for(self.lesson, self.db)
        next_state, plan = await self._run(session_manager.step, self.lesson, state, {})
        lesson_service.persist_plan(self.db, self.lesson, plan)
        self.commit()
        await self.send("lesson_plan_update", self.lesson.plan_json)
        await self.send("progress_snapshot", self._progress_snapshot())
        return next_state

    async def _send_explanation(self, node: Any, segment: Any, replay: bool = False) -> None:
        await self.send(
            "explanation_chunk",
            {
                "node_id": node.node_id,
                "concept": node.concept,
                "title": node.concept,
                "script_text": getattr(segment, "script_text", "") or "",
                "visual_spec": _as_dict(getattr(segment, "visual_spec", None)),
                "avatar_cue": getattr(segment, "avatar_cue", "neutral"),
                "notes": _as_dict(getattr(segment, "notes", None)) or None,
                "depth": getattr(node, "depth", None),
                "est_minutes": getattr(node, "est_minutes", None),
                "replay": replay,
            },
        )

    async def _do_explain(self, state: TeacherState) -> Optional[TeacherState]:
        node = session_manager.current_node(self.lesson)
        if node is None:
            return TeacherState.DONE

        await self.send("ai_state", {"state": "TEACH", "node_id": node.node_id, "concept": node.concept})
        lesson_service.begin_node_explanation(self.db, self.lesson, node.node_id)
        self.commit()

        _, segment = await self._run(session_manager.step, self.lesson, state, {})
        script_text = getattr(segment, "script_text", "") or ""
        visual = _as_dict(getattr(segment, "visual_spec", None))

        lesson_service.mark_node_teaching(self.db, self.lesson, node.node_id, script_text, visual)
        notes = _as_dict(getattr(segment, "notes", None))
        if notes:
            lesson_service.record_notes(self.db, self.lesson, node.node_id, notes)
        self.commit()

        await self._send_explanation(node, segment)
        await self._send_citation(node)

        # DEMONSTRATE enqueues the render; the checkpoint questions are written
        # while it runs, so they cost no extra waiting.
        _, payload = await self._run(
            session_manager.step, self.lesson, TeacherState.DEMONSTRATE, {"segment": segment}
        )
        job_id = payload.get("job_id") if isinstance(payload, dict) else None
        if job_id:
            session_manager.remember_render(self.lesson.id, node.node_id, job_id, script_text)
            await self.send("render_started", {"node_id": node.node_id, "job_id": job_id})

        checkpoints = await self._make_checkpoints(node, segment)
        row = lesson_service.get_node(self.db, self.lesson, node.node_id)
        return await self._deliver_and_teach(node, row, segment, checkpoints, job_id=job_id)

    async def _send_citation(self, node: Any) -> None:
        if not self.lesson.document_id:
            return
        # Provenance is system-generated from retrieval metadata, never the LLM.
        provenance = session_manager.current_provenance(self.lesson)
        chunks = provenance.get("chunks") or []
        risk = provenance.get("risk_level", "low")
        if not chunks:
            chunks = [{"text": text} for text in session_manager.current_grounding(self.lesson)]

        if chunks and risk != "no_document_context":
            top = chunks[0]
            citation = {
                "source_title": getattr(self.lesson.document, "filename", None) or self.lesson.title,
                "excerpt": (top.get("text") or "")[:400],
                "node_id": node.node_id,
                "chunk_id": top.get("chunk_id"),
                "section_title": top.get("section_title"),
                "page_or_slide": top.get("page_or_slide"),
                "chunk_count": len(chunks),
                "risk_level": risk,
                "attempts": provenance.get("attempts", 1),
                "refined_query": provenance.get("refined_query"),
            }
        else:
            citation = {"node_id": node.node_id, "excerpt": "", "risk_level": "no_document_context", "chunk_count": 0}
        lesson_service.record_citation(self.db, self.lesson, node.node_id, citation)
        self.commit()
        await self.send("citation_updated", citation)

    async def _make_checkpoints(self, node: Any, segment: Any) -> dict:
        try:
            pairs = await self._run(session_manager.checkpoint_questions, self.lesson, node, segment)
        except Exception:
            # A concept without questions still teaches; it just can't be checked.
            logger.exception("Checkpoint questions failed for %s", node.node_id)
            pairs = []
        items = [
            {"index": i, "word": word, "at_sec": None, "question": _as_dict(question)}
            for i, (word, question) in enumerate(pairs)
        ]
        data = lesson_service.record_checkpoints(self.db, self.lesson, node.node_id, items)
        self.commit()
        return data

    # -- video + checkpoints --------------------------------------------------

    async def _deliver_and_teach(
        self, node: Any, row: Any, segment: Any, checkpoints: dict,
        job_id: Optional[str] = None, replay: bool = False,
    ) -> Optional[TeacherState]:
        """Get the video to the learner, then run its checkpoints."""
        from modules.backend.src.integrations.container import services

        script = row.script_text or ""
        items = list((checkpoints or {}).get("items") or [])
        media = None

        if row.video_url:
            media = {"video_url": row.video_url, "captions_url": row.captions_url,
                     "duration": row.duration_sec, "captions_path": None}
        else:
            if job_id is None:
                job_id = session_manager.render_job_for(self.lesson.id, node.node_id, script)
            if job_id is None:
                # Finish the render from the SAVED script — never a new LLM call.
                job_id = await self._run(services["avatar_voice_service"].render_segment, segment)
                session_manager.remember_render(self.lesson.id, node.node_id, job_id, script)
                await self.send("render_started", {"node_id": node.node_id, "job_id": job_id})
            outcome, media = await self._await_render(job_id, node)
            if outcome == "gone":
                return None

        if media is not None and items and any(it.get("at_sec") is None for it in items):
            _fill_checkpoint_times(self.db, self.lesson, node.node_id, script, media)
            self.commit()
        self.db.refresh(row)
        checkpoints = row.checkpoints_json or checkpoints
        items = list((checkpoints or {}).get("items") or [])

        since = lesson_service.checkpoints_issued_at(checkpoints)
        passed = lesson_service.answered_checkpoints(self.db, self.lesson, node.node_id, since)
        if media is not None:
            await self.send(
                "video_segment",
                {
                    "node_id": node.node_id,
                    "title": node.concept,
                    "script_text": script,
                    "video_url": media["video_url"],
                    "captions_url": media.get("captions_url"),
                    "duration_sec": media["duration"],
                    "checkpoints": [
                        {"index": it["index"], "at_sec": it["at_sec"]}
                        for it in items if it.get("at_sec") is not None
                    ],
                    "passed": sorted(passed),
                    "replay": replay,
                },
            )
        return await self._teach_video(node, items, passed)

    async def _await_render(self, job_id: str, node: Any) -> tuple[str, Optional[dict]]:
        """("done", media) | ("failed", None) | ("gone", None) if the learner left."""
        from modules.backend.src.integrations.container import services

        avatar = services["avatar_voice_service"]
        script = (lesson_service.get_node(self.db, self.lesson, node.node_id).script_text or "")
        waited = 0.0
        while waited < RENDER_TIMEOUT_SEC:
            if not self.alive:
                _finish_in_background(self.lesson.id, node.node_id, job_id, script)
                return "gone", None
            status = await self._run(avatar.get_status, job_id)

            if status and status.status == "done":
                media = await _attach_once(self.db, self.lesson, node.node_id, script, _as_dict(status.result))
                if media is None:
                    return "gone", None  # superseded explanation; nothing to show
                return "done", media

            if status and status.status == "failed":
                logger.error("Render job %s failed: %s", job_id, status.error)
                lesson_service.log_event(self.db, self.lesson, "render_failed", node_id=node.node_id,
                                         payload={"error": (status.error or "")[:300]})
                self.commit()
                await self.send("render_failed", {"node_id": node.node_id, "reason": status.error or "Rendering failed"})
                return "failed", None

            await asyncio.sleep(RENDER_POLL_SEC)
            waited += RENDER_POLL_SEC

        await self.send("render_failed", {"node_id": node.node_id,
                                          "reason": "Rendering timed out. Continuing with the text explanation."})
        return "failed", None

    async def _teach_video(self, node: Any, items: list, passed: set) -> Optional[TeacherState]:
        """Run the video's checkpoints until it ends or the lesson must adapt."""
        by_index = {it["index"]: it for it in items}

        # A question asked before a drop is still waiting for its answer.
        pending = lesson_service.pending_interaction(self.db, self.lesson, node.node_id)
        if pending is not None and pending.checkpoint_index in by_index:
            outcome = await self._ask_checkpoint(node, by_index[pending.checkpoint_index], pending)
            if outcome is not None:
                return outcome
            passed.add(pending.checkpoint_index)
            await self.send("resume_video", {"node_id": node.node_id, "index": pending.checkpoint_index})

        while self.alive:
            message = await self.next_message()
            payload = message.payload or {}
            if payload.get("node_id") not in (None, node.node_id):
                continue  # late event about an earlier video

            if message.event_type == "checkpoint_reached":
                index = payload.get("index")
                if index in by_index and index not in passed:
                    outcome = await self._ask_checkpoint(node, by_index[index])
                    if outcome is not None:
                        return outcome
                    passed.add(index)
                await self.send("resume_video", {"node_id": node.node_id, "index": index})

            elif message.event_type == "segment_watched":
                # Finished (or no playable video): ask anything not yet asked.
                for index in sorted(set(by_index) - passed):
                    outcome = await self._ask_checkpoint(node, by_index[index])
                    if outcome is not None:
                        return outcome
                    passed.add(index)
                return TeacherState.CONTINUE

            elif message.event_type == "reaction":
                self._log_reaction(message)
            # A stale student_response or anything else is ignored.
        return None

    async def _ask_checkpoint(
        self, node: Any, item: dict, interaction: Optional[Interaction] = None
    ) -> Optional[TeacherState]:
        """Ask one checkpoint question, grade it and adapt.

        Returns None when the learner may carry on with the video, or the state
        to move to (re-explain, rebuild, human)."""
        if interaction is None:
            interaction = lesson_service.record_question(
                self.db, self.lesson, item["question"], checkpoint_index=item["index"]
            )
            self.commit()
        session_manager.restore_question(self.lesson, interaction)

        await self.send("ai_state", {"state": "INTERACT"})
        await self.send(
            "interaction_event",
            {
                "interaction_id": interaction.id,
                "node_id": interaction.node_id,
                "checkpoint_index": item["index"],
                "question_text": interaction.question_text,
                "type": interaction.question_type,
                "options": interaction.options or [],
            },
        )

        if interaction.answered_at and interaction.raw_answer:
            raw_answer, response_time = interaction.raw_answer, interaction.response_time_sec
        else:
            raw_answer, response_time = await self._await_answer(interaction.id)
            lesson_service.record_answer(self.db, interaction, raw_answer, response_time)
            self.commit()

        # Graded as the question type actually asked, never the client's claim.
        response = StudentResponse(
            node_id=interaction.node_id,
            raw_answer=raw_answer,
            response_type=interaction.question_type,
            response_time_sec=float(response_time or 0.0),
        )
        await self.send("ai_state", {"state": "EVALUATE"})
        _, evaluation = await self._run(
            session_manager.step, self.lesson, TeacherState.EVALUATE, {"student_response": response}
        )
        lesson_service.record_evaluation(self.db, self.lesson, interaction, evaluation)
        self.commit()
        await self.send("evaluation_result", {**_as_dict(evaluation), "interaction_id": interaction.id})
        return await self._adapt(interaction, evaluation)

    async def _await_answer(self, interaction_id: str) -> tuple[str, float]:
        """Wait for THIS question's answer. A late or duplicate answer to an
        earlier question must never be taken as the answer to this one."""
        while True:
            message = await self.next_message()
            payload = message.payload or {}
            if message.event_type == "student_response":
                if payload.get("interaction_id") != interaction_id:
                    continue
                raw_answer = str(payload.get("raw_answer", "")).strip()
                if raw_answer:
                    return raw_answer, float(payload.get("response_time_sec") or 0.0)
                await self.send("answer_rejected", {"interaction_id": interaction_id,
                                                    "reason": "Your answer was empty."})
            elif message.event_type == "reaction":
                self._log_reaction(message)

    async def _adapt(self, interaction: Interaction, evaluation: Any) -> Optional[TeacherState]:
        next_state, decision = await self._run(
            session_manager.step, self.lesson, TeacherState.ADAPT, {"eval_result": evaluation}
        )
        lesson_service.record_adaptation(self.db, self.lesson, interaction, decision)
        self.commit()

        await self.send("adaptation_decision", _as_dict(decision))
        await self.send("progress_snapshot", self._progress_snapshot())
        if getattr(decision, "action", None) == "ALLOW":
            return None  # carry on with the same video
        return next_state

    async def _do_continue(self, state: TeacherState) -> Optional[TeacherState]:
        node = session_manager.current_node(self.lesson)
        row = lesson_service.close_node(self.db, self.lesson, node.node_id) if node is not None else None
        if row is not None:
            resolved = escalation_service.on_node_closed(self.db, self.lesson, row)
            if self.lesson.history_reset_at is not None:
                # The fresh count was only for the concept being re-taught:
                # from here on the whole lesson's wrong answers count again.
                self.lesson.history_reset_at = None
                self.db.flush()
                session_manager.reload_history(self.lesson)
            self.commit()
            if resolved is not None:
                await self._run(self._notify_mentor_resolved, resolved)

        point = self.lesson.resume_point
        if row is not None and point and point.get("node_id") == row.node_id:
            return await self._return_from_relearn(point)

        next_state, _ = await self._run(session_manager.step, self.lesson, state, {})
        index = session_manager.sync_index(self.lesson)
        lesson_service.advance_node(self.db, self.lesson, index)
        self.commit()
        await self.send("progress_snapshot", self._progress_snapshot())
        return next_state

    async def _return_from_relearn(self, point: dict) -> Optional[TeacherState]:
        """A relearned concept is done: go back to where the lesson was."""
        escalation_service.finish_relearn(self.lesson)
        nodes = sorted(self.lesson.nodes, key=lambda n: n.position)
        index = point.get("return_index")
        if point.get("return_status") == "completed" or index is None or index >= len(nodes):
            self.commit()
            await self.send("progress_snapshot", self._progress_snapshot())
            return TeacherState.DONE  # re-finish: score and report updated
        self.lesson.current_node_index = index
        self.lesson.fsm_state = point.get("return_fsm") or "EXPLAIN"
        session_manager.get_or_restore(self.lesson).current_node_index = index
        self.commit()
        await self.send("progress_snapshot", self._progress_snapshot())
        await self.send("curriculum_loaded", self.lesson.plan_json)
        # Resume that concept from its saved material — never regenerate it.
        return await self._resume()

    async def _do_done(self, state: TeacherState) -> None:
        pending = escalation_service.concepts_to_review(self.lesson)
        if pending:
            # Not completed until every concept is done: wait at "N to review".
            escalation_service.mark_review_pending(self.lesson)
            self.commit()
            await self.send("progress_snapshot", self._progress_snapshot())
            await self.send("review_needed", {
                "lesson_id": self.lesson.id,
                "concepts": [{"node_id": n.node_id, "concept": n.concept} for n in pending],
            })
            return
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
        node = session_manager.current_node(self.lesson)
        node_id = getattr(node, "node_id", None) or ""
        reason = (
            "This lesson needs a human teacher — several answers in a row show the "
            "explanations are not landing yet."
        )

        concept = getattr(node, "concept", None) or node_id
        esc = escalation_service.open_escalation(self.db, self.lesson, node_id, concept, reason)
        lesson_service.log_event(self.db, self.lesson, "human_escalation", node_id=node_id)
        lesson_service.refresh_learner_profile(self.db, self.user_id)
        self.commit()

        mentor_notified = await self._run(self._notify_mentor, node_id, reason)
        esc.mentor_notified = bool(mentor_notified)
        self.commit()

        await self.send(
            "human_escalation",
            {
                "reason": reason,
                "lesson_id": self.lesson.id,
                "mentor_notified": mentor_notified,
                "escalation": escalation_service.as_dict(esc),
            },
        )

    def _notify_mentor_resolved(self, esc) -> bool:
        """One "resolved — no action needed" note, only if the mentor was alerted."""
        user = self.db.get(User, self.user_id)
        if not user or not user.mentor_email or not esc.mentor_notified:
            return False
        already = any(e.event_type == "mentor_resolved" and e.node_id == esc.node_id for e in self.lesson.events)
        if already:
            return True
        try:
            sent = email_service.send_mentor_resolved(
                user.mentor_email, user.mentor_name or "there", user.full_name, self.lesson.title, esc.concept
            )
        except Exception:
            logger.exception("Mentor resolved email failed for lesson %s", self.lesson.id)
            return False
        if sent:
            lesson_service.log_event(self.db, self.lesson, "mentor_resolved", node_id=esc.node_id)
            self.commit()
        return sent

    def _notify_mentor(self, node_id: str, reason: str) -> bool:
        """Best-effort mentor email. Never allowed to break the escalation itself.

        Runs on the executor thread (blocking SMTP/HTTPS call), guarded by an
        idempotency check so a reconnect never sends a second email for the
        same node.
        """
        user = self.db.get(User, self.user_id)
        if not user or not user.mentor_email:
            logger.info("HUMAN escalation on lesson %s has no mentor on file; email skipped.", self.lesson.id)
            return False

        if lesson_service.already_notified_mentor(self.db, self.lesson, node_id):
            logger.info("Mentor already notified for lesson %s node %s; skipping duplicate.", self.lesson.id, node_id)
            return True

        interaction = lesson_service.latest_interaction(self.db, self.lesson, node_id)
        node = session_manager.current_node(self.lesson)
        concept = getattr(node, "concept", None) or node_id or "this concept"

        try:
            sent = email_service.send_mentor_escalation(
                to_email=user.mentor_email,
                mentor_name=user.mentor_name or "there",
                student_name=user.full_name,
                lesson_title=self.lesson.title,
                concept=concept,
                question_text=getattr(interaction, "question_text", "") or "",
                student_answer=getattr(interaction, "raw_answer", "") or "",
                misconception=getattr(interaction, "misconception_tag", "") or "",
                failure_count=lesson_service.failure_count(self.db, self.lesson, node_id),
                reason=reason,
                report_url=f"{settings.public_base_url}/report.html?lesson={self.lesson.id}",
            )
        except Exception:
            # Escalation must never fail because the mailer did.
            logger.exception("Mentor escalation email failed for lesson %s", self.lesson.id)
            sent = False

        if sent:
            lesson_service.log_event(self.db, self.lesson, "mentor_notified", node_id=node_id)
            self.commit()
        return sent

    # -- helpers -------------------------------------------------------------

    def _progress_snapshot(self) -> dict:
        self.db.refresh(self.lesson)
        nodes = sorted(self.lesson.nodes, key=lambda n: n.position)
        done = sum(1 for n in nodes if n.status in lesson_service.COUNTED_STATUSES)
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
    session.start_reader()
    previous = _ACTIVE.get(lesson_id)
    _ACTIVE[lesson_id] = session

    try:
        if previous is not None and not previous.done.is_set():
            # Take over from the older connection, but let it save the step it
            # is in first, so nothing it already paid for is thrown away.
            await session.send("ai_state", {"state": "RESUME"})
            await previous.supersede()
            try:
                await asyncio.wait_for(previous.done.wait(), PREVIOUS_DRIVER_WAIT_SEC)
            except asyncio.TimeoutError:
                logger.warning("Previous driver for lesson %s did not stop in time", lesson_id)

        user = session.db.get(User, payload["sub"])
        if not user or not user.is_active or not user.is_verified:
            await session.send("error", {}, error="Your account is not authorised.")
            await websocket.close(code=1008)
            return

        if not session.load_lesson():
            await session.send("error", {}, error="Lesson not found.")
            await websocket.close(code=1008)
            return

        if session.lesson.status == "escalated":
            # Paused for a mentor: say so, never silently start teaching again.
            await session.send("lesson_paused", {
                "lesson_id": lesson_id,
                "escalation": escalation_service.as_dict(
                    escalation_service.active_escalation(session.db, session.lesson)),
            })
            session.alive = False
            await websocket.close(code=1000)
            return

        await session.run()
        if session.alive:
            # Lesson finished or handed to a human: close properly, so the
            # browser sees a normal end (1000), not a dropped connection (1006).
            session.alive = False
            await websocket.close(code=1000)

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
        session.alive = False
        session.stop_reader()
        session.close_db()
        session.done.set()
        if _ACTIVE.get(lesson_id) is session:
            del _ACTIVE[lesson_id]
