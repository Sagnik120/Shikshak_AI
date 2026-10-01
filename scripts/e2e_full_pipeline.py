#!/usr/bin/env python3
"""Shikshak AI — full-system end-to-end pipeline check.

Boots the REAL server (uvicorn subprocess) against an isolated, throwaway data
directory and drives it exactly the way the browser does:

  health -> static pages -> signup (OTP read from the response, never email)
  -> verify -> login -> upload a generated Newton's-laws PDF (RAG ingest)
  -> create lesson -> plan -> WS ticket -> live classroom over WebSocket
  (explain -> citation -> avatar/voice render -> checkpoint -> evaluate ->
  adapt, for every node) -> assessment report -> notes -> video/captions
  download -> dashboard/analytics -> topic-only lesson (no document).

Every hop is asserted; the script exits non-zero on the first broken one and
prints a timing table either way.

Usage:
    python scripts/e2e_full_pipeline.py                 # offline LLM (no quota)
    python scripts/e2e_full_pipeline.py --live          # uses GEMINI_API_KEY from .env
    python scripts/e2e_full_pipeline.py --keep          # keep the temp data dir
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
import websockets

ROOT = Path(__file__).resolve().parent.parent

GREEN, RED, YELLOW, BOLD, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[1m", "\033[0m"

NEWTON_TEXT = [
    ("Chapter 1: Newton's First Law (Inertia)",
     "An object at rest stays at rest and an object in motion stays in motion with the same "
     "speed and direction unless acted upon by an unbalanced external force. This tendency to "
     "resist changes in motion is called inertia. The mass of an object is a measure of its "
     "inertia. A passenger lurching forward when a bus brakes suddenly is a classic example."),
    ("Chapter 2: Newton's Second Law (F = ma)",
     "The net force acting on an object equals its mass multiplied by its acceleration, F = m a. "
     "Force is measured in newtons, where one newton accelerates one kilogram at one metre per "
     "second squared. Doubling the force doubles the acceleration; doubling the mass halves it. "
     "Pushing an empty shopping cart is easier than pushing a full one for this reason."),
    ("Chapter 3: Newton's Third Law (Action and Reaction)",
     "For every action there is an equal and opposite reaction. Forces always come in pairs "
     "that act on different bodies. When a rocket expels exhaust gas downward, the gas pushes "
     "the rocket upward. When you swim, you push water backward and the water pushes you forward."),
]


class Failure(Exception):
    pass


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, float, str]] = []

    def ok(self, name: str, started: float, detail: str = "") -> None:
        self.rows.append((name, True, time.perf_counter() - started, detail))
        print(f"  {GREEN}PASS{RESET} {name:<42} {time.perf_counter() - started:7.2f}s  {detail}")

    def fail(self, name: str, started: float, detail: str) -> None:
        self.rows.append((name, False, time.perf_counter() - started, detail))
        print(f"  {RED}FAIL{RESET} {name:<42} {time.perf_counter() - started:7.2f}s  {detail}")


def answer_from(script: str, question: str) -> str:
    """An attentive learner's answer: the narration's sentences that best
    match the question's words."""
    import re

    words = lambda t: {w for w in re.findall(r"[a-z]{4,}", t.lower())}
    want = words(question)
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", script) if len(x.split()) > 4]
    best = sorted(sentences, key=lambda x: -len(want & words(x)))[:3]
    return " ".join(best) or script[:300]


# The test database, so the simulated learner in happy-path scenarios can know
# multiple-choice answers (those scenarios test the flow, not the learner).
TEST_DB = {"path": None}


def known_mcq_answer(interaction_id: str) -> Optional[str]:
    import sqlite3

    if not TEST_DB["path"]:
        return None
    try:
        with sqlite3.connect(TEST_DB["path"]) as conn:
            row = conn.execute("select expected_concept from interactions where id = ?", (interaction_id,)).fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def check(cond: bool, message: str) -> None:
    if not cond:
        raise Failure(message)


def make_pdf(path: Path) -> None:
    """Write a small real text PDF (TrueType-embedded so it's extractable)."""
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["pdf.fonttype"] = 42
    import textwrap

    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(path) as pdf:
        for heading, body in NEWTON_TEXT:
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.08, 0.92, heading, fontsize=16, weight="bold")
            fig.text(0.08, 0.86, "\n".join(textwrap.wrap(body, 80)), fontsize=11, va="top")
            pdf.savefig(fig)
            plt.close(fig)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port: int, data_dir: Path, live: bool, log_path: Path) -> subprocess.Popen:
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "ENVIRONMENT": env.get("ENVIRONMENT", "development"),
            "DATABASE_URL": f"sqlite:///{data_dir / 'e2e.db'}",
            "UPLOAD_ROOT": str(data_dir / "storage"),
            "MEDIA_ROOT": str(data_dir / "media"),
            "CHROMA_PERSIST_DIR": str(data_dir / "chroma"),
            "SECRET_KEY": "e2e-" + uuid.uuid4().hex,
            # The small-instance retrieval profile a free host has to run.
            "EMBEDDING_BACKEND": env.get("EMBEDDING_BACKEND", "e5"),
            "EMBEDDING_MODEL": env.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-small"),
            "RERANKER_ENABLED": env.get("RERANKER_ENABLED", "false"),
            # OTP must come back in the API response and never be emailed.
            "ENABLE_SMTP_SEND": "false",
            "SEED_DEFAULT_USERS": "true",
        }
    )
    if not live:
        env["GEMINI_API_KEY"] = ""  # real env beats .env -> deterministic offline adapter
    log = open(log_path, "w")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "modules.backend.src.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", os.environ.get("UVICORN_LOG_LEVEL", "info")],
        cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT,
    )


class MemorySampler(threading.Thread):
    """Peak resident memory of the server plus its children (ffmpeg etc.) —
    what a container's memory limit actually counts."""

    def __init__(self, pid: int) -> None:
        super().__init__(daemon=True)
        self.pid, self.peak_mb, self._stop = pid, 0.0, threading.Event()

    def _tree_rss_mb(self) -> float:
        out = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,rss="], capture_output=True, text=True).stdout
        rows = [tuple(int(x) for x in line.split()) for line in out.splitlines() if line.strip()]
        tree, frontier = {self.pid}, [self.pid]
        while frontier:
            parent = frontier.pop()
            for pid, ppid, _ in rows:
                if ppid == parent and pid not in tree:
                    tree.add(pid)
                    frontier.append(pid)
        return sum(rss for pid, _, rss in rows if pid in tree) / 1024.0

    def run(self) -> None:
        while not self._stop.wait(0.5):
            try:
                self.peak_mb = max(self.peak_mb, self._tree_rss_mb())
            except Exception:
                pass

    def stop(self) -> float:
        self._stop.set()
        return self.peak_mb


def wait_healthy(base: str, proc: subprocess.Popen, timeout: float = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise Failure(f"server exited during startup (code {proc.returncode})")
        try:
            if httpx.get(f"{base}/health", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise Failure("server did not become healthy in time")


async def run_classroom(base: str, client: httpx.Client, lesson_id: str, report: Report,
                        wrong_first: bool, max_seconds: float, always_wrong: bool = False,
                        drop_after: str = "") -> dict:
    """Drive one live classroom like the real player does.

    The video "plays": at each checkpoint it pauses (checkpoint_reached), the
    question is answered, and it continues only on resume_video; at the end it
    reports segment_watched. drop_after cuts the connection once, the moment
    that event arrives, then reconnects and checks the lesson resumes from
    saved material.
    """
    seen: dict[str, int] = {}
    summary = {"videos": [], "citations": [], "evaluations": [], "decisions": [], "review_needed": None,
               "report": None, "escalated": False, "nodes": 0, "explanations": 0,
               "replays": [], "last_progress": None, "checkpoints": 0}
    answered_wrong = not wrong_first
    last_taught = ""
    tried: dict[str, set] = {}
    scripts: dict[str, str] = {}
    video_urls: set = set()
    received: set = set()
    taught_live: list = []
    plan_size = None
    dropped = False
    dropped_question = None
    deadline = time.monotonic() + max_seconds
    # The player: current video and what it will do next.
    player = {"node": None, "todo": [], "due": None, "action": None, "question_ok": False}
    stale = {"id": None, "sent": False}
    asked: set = set()

    async def send(ws, event_type, payload):
        await ws.send(json.dumps({"event_type": event_type, "payload": payload}))

    def schedule(delay, action):
        player["due"], player["action"] = time.monotonic() + delay, action

    while True:
        r = client.post(f"/api/v1/lessons/{lesson_id}/ticket")
        check(r.status_code == 200, f"ticket: {r.status_code} {r.text}")
        ticket = r.json()
        ws_url = base.replace("http", "ws", 1) + ticket["ws_path"] + "?ticket=" + ticket["ticket"]
        reconnecting = dropped
        async with websockets.connect(ws_url, max_size=2**24, open_timeout=20) as ws:
            player.update(due=None, action=None, question_ok=reconnecting)
            while True:
                remaining = deadline - time.monotonic()
                check(remaining > 0, f"classroom exceeded {max_seconds:.0f}s; events so far: {seen}")
                wait = remaining if player["due"] is None else max(0.0, min(remaining, player["due"] - time.monotonic()))
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=wait)
                except asyncio.TimeoutError:
                    if player["due"] is not None and time.monotonic() >= player["due"]:
                        action, player["due"] = player["action"], None
                        player["question_ok"] = True
                        if action == "watched":
                            await send(ws, "segment_watched", {"node_id": player["node"]})
                        else:
                            await send(ws, "checkpoint_reached", {"node_id": player["node"], "index": action})
                    continue
                msg = json.loads(raw)
                et = msg["event_type"]
                p = msg.get("payload") or {}
                seen[et] = seen.get(et, 0) + 1
                check(et != "error", f"server error event: {msg.get('error')}")

                if drop_after and not dropped and et == drop_after:
                    dropped = True
                    dropped_question = p.get("interaction_id")
                    break  # an abrupt disconnect, before the learner acts

                if et == "curriculum_loaded":
                    summary["nodes"] = len(p.get("nodes") or [])
                    plan_size = plan_size or summary["nodes"]
                elif et == "lesson_plan_update":
                    raise Failure("the lesson plan was rebuilt mid-lesson (REGENERATE must rebuild one segment only)")
                elif et == "progress_snapshot":
                    summary["last_progress"] = p
                elif et == "explanation_chunk":
                    node = p.get("node_id")
                    check(len((p.get("script_text") or "").split()) >= 40, f"script too short for {node}")
                    check(player["due"] is None or player["node"] == node or reconnecting,
                          f"started {node} while {player['node']} was still playing")
                    if p.get("replay") and reconnecting and node in scripts:
                        check(p["script_text"] == scripts[node],
                              f"reconnect regenerated the script for {node} instead of replaying it")
                    if p.get("replay"):
                        summary["replays"].append(p)
                    if not p.get("replay"):
                        taught_live.append(node)
                    if not p.get("replay") or (node, p["script_text"]) not in received:
                        summary["explanations"] += 1
                    received.add((node, p["script_text"]))
                    scripts[node] = p["script_text"]
                    player.update(node=None, todo=[], due=None)
                    notes = p.get("notes") or {}
                    last_taught = " ".join((notes.get("key_points") or [])[:2]) or p.get("script_text", "")[:300]
                elif et == "citation_updated":
                    summary["citations"].append(p)
                elif et == "render_failed":
                    raise Failure(f"render failed for {p.get('node_id')}: {p.get('reason')}")
                elif et == "video_segment":
                    url, dur = p.get("video_url"), float(p.get("duration_sec") or 0)
                    cps = sorted(p.get("checkpoints") or [], key=lambda c: c["at_sec"])
                    if p.get("replay"):
                        summary["replays"].append(p)
                    else:
                        check(url not in video_urls, f"the same video was delivered twice: {url}")
                        summary["videos"].append(p)
                        check(cps, f"video for {p.get('node_id')} has no mid-video checkpoints")
                        for c in cps:
                            check(0 < c["at_sec"] < dur, f"checkpoint at {c['at_sec']}s is not mid-video ({dur}s)")
                        summary["checkpoints"] += len(cps)
                    video_urls.add(url)
                    passed = set(p.get("passed") or [])
                    # After a reconnect the question that was on screen is re-asked
                    # straight away (the player is already paused at it).
                    player.update(node=p.get("node_id"), question_ok=bool(reconnecting and dropped_question),
                                  todo=[c["index"] for c in cps if c["index"] not in passed])
                    schedule(1.0, player["todo"].pop(0) if player["todo"] else "watched")
                elif et == "resume_video":
                    player["question_ok"] = False
                    schedule(1.0, player["todo"].pop(0) if player["todo"] else "watched")
                elif et == "interaction_event":
                    # Questions come only when the video pauses at a checkpoint.
                    check(player["question_ok"], f"question arrived mid-video with no checkpoint: {p.get('question_text')}")
                    if reconnecting and dropped_question:
                        check(p.get("interaction_id") == dropped_question,
                              "reconnect asked a NEW question instead of the one on screen")
                        dropped_question = None
                    asked.add(p["interaction_id"])
                    if p.get("checkpoint_index") in player["todo"]:
                        player["todo"].remove(p["checkpoint_index"])
                    node = p["node_id"]
                    opts = p.get("options") or []
                    done = tried.setdefault(node, set())
                    if always_wrong or not answered_wrong:
                        answer, answered_wrong = "no idea", True
                    elif opts and known_mcq_answer(p["interaction_id"]) in opts:
                        answer = known_mcq_answer(p["interaction_id"])
                    elif opts:
                        # The option the narration best supports; after a miss, the next best.
                        support = answer_from(scripts.get(node, last_taught), p.get("question_text", "")).lower()
                        ranked = sorted(opts, key=lambda o: -sum(w in support for w in o.lower().split() if len(w) > 3))
                        answer = next((o for o in ranked if o not in done), ranked[0])
                    else:
                        answer = answer_from(scripts.get(node, last_taught), p.get("question_text", ""))
                    done.add(answer)
                    await send(ws, "student_response", {"interaction_id": p["interaction_id"], "raw_answer": answer,
                                                        "response_type": p.get("type"), "response_time_sec": 4.2})
                    if not stale["sent"]:
                        # A double-click: the same answer again. It must never be
                        # taken as the answer to the NEXT question.
                        stale.update(id=p["interaction_id"], sent=True)
                        await send(ws, "student_response", {"interaction_id": p["interaction_id"],
                                                            "raw_answer": "stale duplicate", "response_time_sec": 0.1})
                elif et == "evaluation_result":
                    summary["evaluations"].append(p)
                elif et == "adaptation_decision":
                    summary["decisions"].append(p.get("action"))
                elif et == "assessment_report":
                    summary["report"] = p
                    break
                elif et == "human_escalation":
                    summary["escalated"] = True
                    break
                elif et == "review_needed":
                    summary["review_needed"] = p.get("concepts") or []
                    break
        if summary["report"] or summary["escalated"] or summary.get("review_needed"):
            break
        check(dropped and not reconnecting, f"connection ended unexpectedly; events: {seen}")
    summary["events"] = seen
    summary["taught_live"] = taught_live
    # Each question graded exactly once; the stale duplicate answer never counts.
    graded = [e.get("interaction_id") for e in summary["evaluations"]]
    check(len(graded) == len(set(graded)), f"a question was graded twice: {graded}")
    check(len(graded) == len(asked), f"{len(graded)} gradings for {len(asked)} questions asked")
    return summary


async def check_single_driver(base: str, client: httpx.Client, lesson_id: str) -> int:
    """A second connection must take over and close the first (code 4001)."""
    def url():
        t = client.post(f"/api/v1/lessons/{lesson_id}/ticket").json()
        return base.replace("http", "ws", 1) + t["ws_path"] + "?ticket=" + t["ticket"]

    first = await websockets.connect(url())
    await first.recv()  # session_ready
    second = await websockets.connect(url())
    try:
        await asyncio.wait_for(first.wait_closed(), timeout=30)
        return first.close_code
    finally:
        await second.close()


async def open_classroom(base: str, client: httpx.Client, lesson_id: str, until: str, seconds: float = 120):
    """Connect, collect events until `until` (or the socket closes). Returns
    (events, open websocket or None, close code)."""
    t = client.post(f"/api/v1/lessons/{lesson_id}/ticket").json()
    ws = await websockets.connect(base.replace("http", "ws", 1) + t["ws_path"] + "?ticket=" + t["ticket"],
                                  max_size=2**24)
    events = []
    try:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=deadline - time.monotonic()))
            events.append(msg)
            if msg["event_type"] == until:
                return events, ws, None
    except websockets.ConnectionClosed as exc:
        return events, None, exc.rcvd.code if exc.rcvd else None
    except asyncio.TimeoutError:
        pass
    return events, ws, None


def detail(client: httpx.Client, lesson_id: str) -> dict:
    r = client.get(f"/api/v1/lessons/{lesson_id}")
    check(r.status_code == 200, f"lesson detail {r.status_code}")
    return r.json()


def node_by_id(lesson: dict, node_id: str) -> dict:
    return next(n for n in lesson["nodes"] if n["node_id"] == node_id)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="use the real Gemini key from .env")
    ap.add_argument("--keep", action="store_true", help="keep the temp data directory")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--budget", type=int, default=5, help="lesson time budget (minutes)")
    ap.add_argument("--max-mb", type=float, default=0, help="fail if peak server memory exceeds this")
    args = ap.parse_args()

    data_dir = Path(tempfile.mkdtemp(prefix="shikshak_e2e_"))
    TEST_DB["path"] = str(data_dir / "e2e.db")
    log_path = data_dir / "server.log"
    port = args.port or free_port()
    base = f"http://127.0.0.1:{port}"
    report = Report()
    print(f"{BOLD}Shikshak AI end-to-end ({'LIVE Gemini' if args.live else 'offline LLM'}){RESET}")
    print(f"  data dir: {data_dir}\n  server log: {log_path}\n")

    proc = start_server(port, data_dir, args.live, log_path)
    sampler = MemorySampler(proc.pid)
    sampler.start()
    step, t = "server boot + /health", time.perf_counter()
    exit_code = 1
    try:
        wait_healthy(base, proc)
        report.ok(step, t)

        client = httpx.Client(base_url=base, timeout=httpx.Timeout(300.0, connect=10.0))

        step, t = "static frontend pages", time.perf_counter()
        pages = ["/", "/login.html", "/signup.html", "/verify.html", "/dashboard.html",
                 "/new-lesson.html", "/classroom.html", "/report.html", "/lessons.html",
                 "/analytics.html", "/settings.html", "/forgot-password.html",
                 "/reset-password.html", "/js/api.js", "/css/"]
        for page in pages[:-1]:
            r = client.get(page)
            check(r.status_code == 200, f"{page} -> {r.status_code}")
        report.ok(step, t, f"{len(pages) - 1} assets")

        # ---- auth: OTP must be on screen, never mailed -------------------
        step, t = "signup returns on-screen OTP", time.perf_counter()
        email = f"e2e_{uuid.uuid4().hex[:8]}@example.com"
        password = "E2eStudent#2026"
        r = client.post("/api/v1/auth/signup", json={
            "full_name": "E2E Learner", "email": email, "password": password,
            "preferred_level": "beginner", "preferred_language": "en"})
        check(r.status_code == 201, f"signup {r.status_code}: {r.text}")
        otp = r.json().get("dev_otp")
        check(bool(otp) and otp.isdigit(), f"no dev_otp in signup response: {r.json()}")
        report.ok(step, t, f"otp={otp}")

        step, t = "resend OTP (cooldown respected)", time.perf_counter()
        r = client.post("/api/v1/auth/resend-otp", json={"email": email, "purpose": "verify_email"})
        check(r.status_code in (200, 429), f"resend {r.status_code}: {r.text}")
        if r.status_code == 200 and r.json().get("dev_otp"):
            otp = r.json()["dev_otp"]
        report.ok(step, t, f"status {r.status_code}")

        step, t = "verify email with OTP", time.perf_counter()
        r = client.post("/api/v1/auth/verify-email", json={"email": email, "code": otp})
        check(r.status_code == 200, f"verify {r.status_code}: {r.text}")
        report.ok(step, t)

        step, t = "login + /auth/me", time.perf_counter()
        r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        check(r.status_code == 200, f"login {r.status_code}: {r.text}")
        tokens = r.json()
        client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
        r = client.get("/api/v1/auth/me")
        check(r.status_code == 200 and r.json()["email"] == email, f"/me {r.status_code}")
        report.ok(step, t)

        step, t = "token refresh", time.perf_counter()
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        check(r.status_code == 200, f"refresh {r.status_code}: {r.text}")
        client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        report.ok(step, t)

        step, t = "forgot-password returns on-screen OTP", time.perf_counter()
        r = client.post("/api/v1/auth/forgot-password", json={"email": email})
        check(r.status_code == 200 and r.json().get("dev_otp"), f"forgot {r.status_code}: {r.text}")
        report.ok(step, t)

        # ---- RAG ingest ---------------------------------------------------
        step, t = "upload PDF -> RAG ingest", time.perf_counter()
        pdf = data_dir / "newtons_laws.pdf"
        make_pdf(pdf)
        with open(pdf, "rb") as fh:
            r = client.post("/api/v1/lessons/documents",
                            files={"file": ("newtons_laws.pdf", fh, "application/pdf")})
        check(r.status_code == 201, f"upload {r.status_code}: {r.text}")
        doc = r.json()
        check(doc["status"] == "ready" and doc["chunk_count"] > 0, f"bad ingest: {doc}")
        junk = {"one", "you", "your", "an", "the", "when", "this"}
        bad_terms = [k for k in doc["key_terms"] if set(k.lower().split()) & junk]
        check(not bad_terms, f"stopwords in key terms: {bad_terms}")
        report.ok(step, t, f"{doc['chunk_count']} chunks, terms={doc['key_terms'][:4]}")

        step, t = "reject unsupported upload", time.perf_counter()
        r = client.post("/api/v1/lessons/documents", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
        check(r.status_code == 415, f"expected 415, got {r.status_code}")
        report.ok(step, t)

        # ---- document lesson ---------------------------------------------
        step, t = "create lesson (document)", time.perf_counter()
        r = client.post("/api/v1/lessons", json={
            "topic": "Newton's Laws of Motion", "document_id": doc["document_id"],
            "level": "beginner", "language": "en", "time_budget_min": args.budget,
            "style": "visual"})
        check(r.status_code == 201, f"create {r.status_code}: {r.text}")
        lesson_id = r.json()["lesson_id"]
        report.ok(step, t)

        step, t = "generate plan (RAG -> Planner)", time.perf_counter()
        r = client.post(f"/api/v1/lessons/{lesson_id}/plan")
        check(r.status_code == 200, f"plan {r.status_code}: {r.text}")
        nodes = r.json()["plan"]["nodes"]
        check(len(nodes) >= 1, "empty plan")
        report.ok(step, t, f"{len(nodes)} nodes: {[n['concept'][:28] for n in nodes]}")

        step, t = "live classroom (document lesson)", time.perf_counter()
        summary = asyncio.run(run_classroom(base, client, lesson_id, report,
                                            wrong_first=True, max_seconds=1500))
        check(summary["report"] is not None or summary["escalated"],
              f"classroom ended without report: {summary['events']}")
        check(not summary["escalated"], "lesson escalated to HUMAN in the happy path")
        check(len(summary["videos"]) >= 1, "no video segments rendered")
        grounded = [c for c in summary["citations"] if c.get("risk_level") != "no_document_context"]
        check(len(grounded) >= 1, f"no grounded citation reached the classroom: {summary['citations']}")
        check(any(not e.get("correct") for e in summary["evaluations"]), "wrong answer was not graded wrong")
        progress = summary["last_progress"] or {}
        check(progress.get("nodes_completed") == progress.get("node_count"),
              f"progress bar stuck at {progress.get('nodes_completed')}/{progress.get('node_count')}")
        explanations = summary["explanations"]
        report.ok(step, t, f"{len(summary['videos'])} videos, decisions={summary['decisions']}")

        rep = summary["report"]
        step, t = "assessment report contract", time.perf_counter()
        for key in ("score_pct", "strong_areas", "weak_areas", "recommended_next", "narrative_feedback"):
            check(key in rep, f"report missing {key}")
        check(0 <= float(rep["score_pct"]) <= 100, f"score_pct out of range {rep['score_pct']}")
        check(bool(rep["narrative_feedback"]), "empty narrative")
        report.ok(step, t, f"score={rep['score_pct']}")

        step, t = "video + captions served", time.perf_counter()
        durations = []
        for v in summary["videos"]:
            r = client.get(v["video_url"])
            check(r.status_code == 200 and len(r.content) > 10_000, f"video {v['video_url']} -> {r.status_code}")
            check(r.content[4:8] == b"ftyp", "video is not an MP4")
            durations.append(v["duration_sec"])
            if v.get("captions_url"):
                c = client.get(v["captions_url"])
                check(c.status_code == 200 and c.text.startswith("WEBVTT"), f"captions -> {c.status_code}")
        report.ok(step, t, f"durations={[round(d) for d in durations]}s")

        step, t = "lesson detail / notes / trace", time.perf_counter()
        r = client.get(f"/api/v1/lessons/{lesson_id}")
        check(r.status_code == 200 and r.json().get("status") == "completed", f"detail {r.text[:300]}")
        r = client.get(f"/api/v1/lessons/{lesson_id}/notes", params={"format": "markdown"})
        check(r.status_code == 200 and len(r.text) > 100, f"notes {r.status_code}")
        r = client.get(f"/api/v1/lessons/{lesson_id}/trace")
        check(r.status_code == 200, f"trace {r.status_code}")
        report.ok(step, t)

        step, t = "dashboard / analytics / profile", time.perf_counter()
        for path in ("/api/v1/dashboard", "/api/v1/analytics", "/api/v1/profile/learning",
                     "/api/v1/lessons", "/api/v1/lessons/documents", "/api/v1/account/profile"):
            r = client.get(path)
            check(r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}")
        report.ok(step, t)

        step, t = "reconnect to finished lesson", time.perf_counter()
        r = client.post(f"/api/v1/lessons/{lesson_id}/ticket")
        check(r.status_code in (200, 409), f"ticket after completion {r.status_code}")
        report.ok(step, t, f"status {r.status_code}")

        # ---- topic-only lesson (no document) ------------------------------
        step, t = "topic-only lesson end-to-end", time.perf_counter()
        r = client.post("/api/v1/lessons", json={
            "topic": "Photosynthesis", "level": "beginner", "language": "en",
            "time_budget_min": 5, "style": "analogy"})
        check(r.status_code == 201, f"create {r.status_code}: {r.text}")
        lesson2 = r.json()["lesson_id"]
        r = client.post(f"/api/v1/lessons/{lesson2}/plan")
        check(r.status_code == 200, f"plan {r.status_code}: {r.text}")
        s2 = asyncio.run(run_classroom(base, client, lesson2, report, wrong_first=False, max_seconds=1500))
        check(s2["report"] is not None, f"no report: {s2['events']}")
        check(not any(c.get("excerpt") for c in s2["citations"]), "topic lesson produced citations")
        explanations += s2["explanations"]
        report.ok(step, t, f"{len(s2['videos'])} videos, score={s2['report']['score_pct']}")

        def new_topic_lesson(topic: str) -> str:
            r = client.post("/api/v1/lessons", json={"topic": topic, "time_budget_min": 5})
            check(r.status_code == 201, f"create {r.status_code}: {r.text}")
            lid = r.json()["lesson_id"]
            check(client.post(f"/api/v1/lessons/{lid}/plan").status_code == 200, "plan failed")
            return lid

        # Issue 2: a dropped connection must resume from saved material.
        # ai_state = the LLM is still writing the script when the line drops.
        for drop in ("ai_state", "video_segment", "render_started", "interaction_event"):
            step, t = f"disconnect after {drop} -> resume", time.perf_counter()
            s = asyncio.run(run_classroom(base, client, new_topic_lesson("Gravity"), report,
                                          wrong_first=False, max_seconds=1500, drop_after=drop))
            check(s["report"] is not None, f"no report after reconnect: {s['events']}")
            check(s["replays"], "reconnect did not replay the concept in progress")
            explanations += s["explanations"]
            report.ok(step, t, f"{len(s['replays'])} replayed, {len(s['videos'])} videos")

        step, t = "repeated wrong answers -> HUMAN", time.perf_counter()
        r = client.post("/api/v1/lessons", json={"topic": "Fractions", "time_budget_min": 5})
        lesson3 = r.json()["lesson_id"]
        check(client.post(f"/api/v1/lessons/{lesson3}/plan").status_code == 200, "plan failed")
        s3 = asyncio.run(run_classroom(base, client, lesson3, report, wrong_first=True,
                                       max_seconds=1500, always_wrong=True))
        check(s3["escalated"], f"no escalation: decisions={s3['decisions']}")
        explanations += s3["explanations"]
        # wrong -> MODIFY; wrong again -> REGENERATE (this segment); > 3 wrong in the lesson -> HUMAN
        check(s3["decisions"] == ["MODIFY", "REGENERATE", "REGENERATE", "HUMAN"], f"decisions={s3['decisions']}")
        r = client.get(f"/api/v1/lessons/{lesson3}")
        check(r.json().get("status") == "escalated", f"status={r.json().get('status')}")
        report.ok(step, t, f"decisions={s3['decisions']}")

        step, t = "no hidden LLM regeneration", time.perf_counter()
        calls = log_path.read_text(errors="replace").count("Explainer node=")
        check(calls == explanations, f"{calls} explainer LLM calls for {explanations} delivered explanations")
        report.ok(step, t, f"{calls} calls = {explanations} explanations")


        # ======== Review, practice, pause / continue / skip / learn again ========
        started_at = time.time()

        step, t = "paused lesson never auto-teaches", time.perf_counter()
        events, ws, code = asyncio.run(open_classroom(base, client, lesson3, until="explanation_chunk", seconds=20))
        kinds = [e["event_type"] for e in events]
        check("lesson_paused" in kinds, f"no lesson_paused notice: {kinds}")
        check("explanation_chunk" not in kinds and "render_started" not in kinds, f"paused lesson taught again: {kinds}")
        check(code == 1000, f"paused lesson closed with {code}, expected a normal close")
        report.ok(step, t)

        step, t = "practice never changes the lesson", time.perf_counter()
        before = detail(client, lesson_id)
        r = client.get(f"/api/v1/lessons/{lesson_id}/practice")
        check(r.status_code == 200 and r.json()["questions"], f"practice list {r.status_code}: {r.text[:200]}")
        questions = r.json()["questions"]
        check("expected_concept" not in questions[0], "practice leaked the answer key")
        for q in questions[:3]:
            answer = q["options"][0] if q["options"] else "Objects keep moving unless a force acts on them."
            r = client.post(f"/api/v1/lessons/{lesson_id}/practice/{q['interaction_id']}", json={"answer": answer})
            check(r.status_code == 200 and "correct" in r.json(), f"practice answer {r.status_code}: {r.text[:200]}")
        after = detail(client, lesson_id)
        same = lambda d: (d["status"], d["report"]["score_pct"], d["progress_pct"],
                          [(n["status"], n["mastery_score"], len(n["interactions"])) for n in d["nodes"]])
        check(same(before) == same(after), "practice changed the lesson's score, progress or answers")
        report.ok(step, t, f"{len(questions)} questions, lesson unchanged")

        step, t = "skip paused concept -> needs review", time.perf_counter()
        paused = detail(client, lesson3)
        stuck = paused["escalation"]["node_id"]
        r = client.post(f"/api/v1/lessons/{lesson3}/skip")
        check(r.status_code == 200, f"skip {r.status_code}: {r.text[:200]}")
        d = detail(client, lesson3)
        check(d["status"] == "in_progress", f"after skip status={d['status']}")
        check(node_by_id(d, stuck)["review_note"] == "needs review", "skipped concept not marked for review")
        check(client.post(f"/api/v1/lessons/{lesson3}/skip").status_code == 409, "second skip was allowed")
        attention = client.get("/api/v1/dashboard").json()["needs_attention"]
        check(any(a["kind"] == "review" and a["node_id"] == stuck for a in attention), f"dashboard missing review item: {attention}")
        report.ok(step, t)

        step, t = "learn again while classroom is open", time.perf_counter()
        remaining = [n for n in d["nodes"] if n["position"] > node_by_id(d, stuck)["position"]]
        other_scripts = {}
        if remaining:
            async def relearn_with_open_tab():
                # Watch the next concept long enough that it has a saved video,
                # then press "Learn this again" from another page.
                events, ws, code = await open_classroom(base, client, lesson3, until="video_segment")
                check(ws is not None, f"classroom closed early ({code}): {[e['event_type'] for e in events]}")
                other_scripts.update({n["node_id"]: n["script_text"] for n in detail(client, lesson3)["nodes"]
                                      if n["node_id"] != stuck and n["script_text"]})
                loop = asyncio.get_running_loop()
                reply = await loop.run_in_executor(
                    None, lambda: client.post(f"/api/v1/lessons/{lesson3}/nodes/{stuck}/relearn"))
                try:
                    await asyncio.wait_for(ws.recv(), timeout=5)
                except websockets.ConnectionClosed as exc:
                    return reply, exc.rcvd.code if exc.rcvd else None
                except asyncio.TimeoutError:
                    return reply, "still open"
                return reply, "still open"

            reply, closed = asyncio.run(relearn_with_open_tab())
            check(closed == 4001, f"the open classroom was not handed over safely (close={closed})")
        else:
            reply = client.post(f"/api/v1/lessons/{lesson3}/nodes/{stuck}/relearn")
        check(reply.status_code == 200, f"relearn {reply.status_code}: {reply.text[:200]}")
        s4 = asyncio.run(run_classroom(base, client, lesson3, report, wrong_first=False, max_seconds=1500))
        check(s4["report"] is not None, f"relearn lesson did not finish: {s4['events']}")
        check(s4["taught_live"] and s4["taught_live"][0] == stuck, f"relearn taught {s4['taught_live']} first")
        check(s4["taught_live"].count(stuck) == 1 and all(
            n not in other_scripts for n in s4["taught_live"]), f"relearn re-taught other concepts: {s4['taught_live']}")
        d = detail(client, lesson3)
        n = node_by_id(d, stuck)
        check(n["status"] == "mastered" and n["review_note"] == "after review", f"relearned node: {n['status']}/{n['review_note']}")
        for node_id, script in other_scripts.items():
            check(node_by_id(d, node_id)["script_text"] == script, f"{node_id} was regenerated")
        check(d["escalations"][-1]["status"] == "resolved", f"escalation after relearn: {d['escalations'][-1]['status']}")
        check(d["status"] == "completed" and d["report"], "lesson not re-finished with a report")
        attention = client.get("/api/v1/dashboard").json()["needs_attention"]
        check(not [a for a in attention if a["lesson_id"] == lesson3], f"dashboard still flags lesson: {attention}")
        report.ok(step, t, f"taught {s4['taught_live']}, others untouched")

        step, t = "continue after pause -> resolved", time.perf_counter()
        r = client.patch("/api/v1/account/profile", json={"mentor_name": "Asha Mentor", "mentor_email": "mentor@example.com"})
        check(r.status_code == 200, f"set mentor {r.status_code}: {r.text[:200]}")
        r = client.post("/api/v1/lessons", json={"topic": "Magnetism", "time_budget_min": 5})
        lesson5 = r.json()["lesson_id"]
        check(client.post(f"/api/v1/lessons/{lesson5}/plan").status_code == 200, "plan failed")
        s5 = asyncio.run(run_classroom(base, client, lesson5, report, wrong_first=True, max_seconds=1500, always_wrong=True))
        check(s5["escalated"], "no escalation")
        d = detail(client, lesson5)
        stuck5 = d["escalation"]["node_id"]
        check(d["escalation"]["mentor_notified"], "mentor was not notified")
        check(client.post(f"/api/v1/lessons/{lesson5}/continue").status_code == 200, "continue failed")
        check(client.post(f"/api/v1/lessons/{lesson5}/continue").status_code == 409, "second continue was allowed")
        s6 = asyncio.run(run_classroom(base, client, lesson5, report, wrong_first=False, max_seconds=1500))
        check(s6["report"] is not None, f"lesson did not finish after continue: {s6['events']}")
        check(s6["taught_live"][0] == stuck5, f"continue did not restart the stuck concept: {s6['taught_live']}")
        check(s6["decisions"] and "HUMAN" not in s6["decisions"], f"fresh count not applied: {s6['decisions']}")
        d = detail(client, lesson5)
        check(d["escalations"][0]["status"] == "resolved", f"escalation {d['escalations'][0]['status']}")
        check(node_by_id(d, stuck5)["review_note"] == "after help", "concept not marked mastered after help")
        outbox = ROOT / "data" / "outbox"
        resolved_mail = [f for f in outbox.glob("*.json") if f.stat().st_mtime >= started_at
                         and "Resolved:" in f.read_text(errors="replace")]
        check(len(resolved_mail) == 1, f"expected one 'resolved' note to the mentor, found {len(resolved_mail)}")
        report.ok(step, t)

        step, t = "skip keeps counting wrong answers", time.perf_counter()
        r = client.post("/api/v1/lessons", json={"topic": "Light", "time_budget_min": 6})
        lesson8 = r.json()["lesson_id"]
        check(client.post(f"/api/v1/lessons/{lesson8}/plan").status_code == 200, "plan failed")
        s8 = asyncio.run(run_classroom(base, client, lesson8, report, wrong_first=True, max_seconds=1500, always_wrong=True))
        check(s8["escalated"], "no escalation")
        check(client.post(f"/api/v1/lessons/{lesson8}/skip").status_code == 200, "skip failed")
        s8b = asyncio.run(run_classroom(base, client, lesson8, report, wrong_first=True, max_seconds=1500, always_wrong=True))
        check(s8b["escalated"] and s8b["decisions"] == ["HUMAN"],
              f"after a skip, one more wrong answer should escalate: {s8b['decisions']}")
        report.ok(step, t, "1 wrong answer after the skip -> HUMAN")

        step, t = "concepts to review -> not completed", time.perf_counter()
        r = client.post("/api/v1/lessons", json={"topic": "Heat", "time_budget_min": 6})
        lesson7 = r.json()["lesson_id"]
        check(client.post(f"/api/v1/lessons/{lesson7}/plan").status_code == 200, "plan failed")
        s7 = asyncio.run(run_classroom(base, client, lesson7, report, wrong_first=True, max_seconds=1500, always_wrong=True))
        check(s7["escalated"], "no escalation")
        stuck7 = detail(client, lesson7)["escalation"]["node_id"]
        check(client.post(f"/api/v1/lessons/{lesson7}/skip").status_code == 200, "skip failed")
        s7b = asyncio.run(run_classroom(base, client, lesson7, report, wrong_first=False, max_seconds=1500))
        check(s7b["review_needed"] and s7b["review_needed"][0]["node_id"] == stuck7,
              f"lesson end did not ask to review the skipped concept: {s7b['events']}")
        check(s7b["report"] is None, "a lesson with a concept to review was completed")
        d = detail(client, lesson7)
        check(d["status"] == "in_progress" and d["review_pending"] and d["to_review"] == 1, f"status {d['status']} / {d['to_review']}")
        check(d["nodes_completed"] == d["node_count"] - 1 and not d["report"], f"progress {d['nodes_completed']}/{d['node_count']}")
        # Reopening shows the same "to review" end, never re-teaching anything.
        async def reopen():
            events, ws, code = await open_classroom(base, client, lesson7, until="review_needed", seconds=20)
            if ws is not None:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=10)
                except websockets.ConnectionClosed as exc:
                    code = exc.rcvd.code if exc.rcvd else None
                except asyncio.TimeoutError:
                    code = "still open"
            return events, code

        events, code = asyncio.run(reopen())
        kinds = [e["event_type"] for e in events]
        check("review_needed" in kinds and "explanation_chunk" not in kinds, f"reopen: {kinds}")
        check(code == 1000, f"lesson waiting for review should close normally ({code})")
        check(client.post(f"/api/v1/lessons/{lesson7}/nodes/{stuck7}/relearn").status_code == 200, "review next failed")
        s7c = asyncio.run(run_classroom(base, client, lesson7, report, wrong_first=False, max_seconds=1500))
        check(s7c["report"] is not None and s7c["taught_live"] == [stuck7], f"review run: {s7c['taught_live']} {s7c['events']}")
        d = detail(client, lesson7)
        check(d["status"] == "completed" and d["nodes_completed"] == d["node_count"] and not d["to_review"],
              f"after review: {d['status']} {d['nodes_completed']}/{d['node_count']}")
        report.ok(step, t, "1/2 to review -> review next -> completed 2/2")

        step, t = "video finishes after learner leaves", time.perf_counter()
        r = client.post("/api/v1/lessons", json={"topic": "Sound waves", "time_budget_min": 5})
        lesson6 = r.json()["lesson_id"]
        check(client.post(f"/api/v1/lessons/{lesson6}/plan").status_code == 200, "plan failed")
        async def leave_mid_render():
            events, ws, code = await open_classroom(base, client, lesson6, until="render_started")
            check(ws is not None, "classroom closed before rendering")
            await ws.close()  # leave mid-render

        asyncio.run(leave_mid_render())
        first = None
        for _ in range(240):
            first = next((n for n in detail(client, lesson6)["nodes"] if n["script_text"]), None)
            if first and first["video_url"]:
                break
            time.sleep(0.5)
        check(first and first["video_url"], "the video was not saved after the learner left")
        async def come_back():
            events, ws, code = await open_classroom(base, client, lesson6, until="video_segment")
            if ws is not None:
                await ws.close()
            return events

        events = asyncio.run(come_back())
        kinds = [e["event_type"] for e in events]
        video = events[-1]["payload"] if kinds and kinds[-1] == "video_segment" else {}
        check(video.get("video_url") == first["video_url"] and video.get("replay"), f"not the saved video: {kinds}")
        check("render_started" not in kinds, "the video was rendered a second time")
        report.ok(step, t)

        step, t = "second tab takes over (single driver)", time.perf_counter()
        code = asyncio.run(check_single_driver(base, client, new_topic_lesson("Magnets")))
        check(code == 4001, f"first connection close code {code}, expected 4001")
        report.ok(step, t)

        step, t = "invalid WS ticket rejected", time.perf_counter()

        async def bad_ticket() -> str:
            url = base.replace("http", "ws", 1) + f"/api/v1/lessons/{lesson2}/live?ticket=bogus"
            async with websockets.connect(url) as ws:
                return json.loads(await ws.recv())["event_type"]

        check(asyncio.run(bad_ticket()) == "error", "bogus ticket accepted")
        report.ok(step, t)

        step, t = "server log has no tracebacks", time.perf_counter()
        log_text = log_path.read_text(errors="replace")
        check("Traceback" not in log_text, "traceback in server log — see " + str(log_path))
        report.ok(step, t)

        peak = sampler.peak_mb
        step, t = "peak server memory", time.perf_counter()
        check(not args.max_mb or peak <= args.max_mb, f"{peak:.0f} MB > limit {args.max_mb:.0f} MB")
        report.ok(step, t, f"{peak:.0f} MB (server + ffmpeg children)")
        exit_code = 0
    except Failure as exc:
        report.fail(step, t, str(exc))
    except Exception as exc:  # unexpected crash in the harness or the server
        report.fail(step, t, f"{type(exc).__name__}: {exc}")
    finally:
        sampler.stop()
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

    passed = sum(1 for r in report.rows if r[1])
    colour = GREEN if exit_code == 0 else RED
    print(f"\n{colour}{BOLD}{passed}/{len(report.rows)} steps passed{RESET}")
    if exit_code != 0:
        print(f"{YELLOW}server log tail:{RESET}")
        print("\n".join(log_path.read_text(errors="replace").splitlines()[-40:]))
    if args.keep or exit_code != 0:
        print(f"data kept at {data_dir}")
    else:
        shutil.rmtree(data_dir, ignore_errors=True)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
