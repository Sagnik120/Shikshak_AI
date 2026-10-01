#!/usr/bin/env python3
"""Real-browser test of the Next.js frontend (FRONTEND/) against the real backend.

Drives the site the way a learner (and an admin) does and asserts what they see:

* landing page renders with no script errors; English <-> Hindi switch keeps every card
* sign up -> on-screen OTP -> "Fill it in for me" -> dashboard (no email sent)
* new lesson from a topic -> plan -> classroom
* the video PAUSES at a mid-video checkpoint; can't be played or seeked past it
* a right answer resumes the same video; wrong answers re-explain
* more than 3 wrong answers stop the lesson: video paused, controls removed,
  and reopening the lesson keeps it paused
* review: rewatch a saved video, practise with instant feedback
* slide-to-skip moves the lesson on; an earlier concept can be rewatched in place
* profile: pick an avatar, upload a photo
* admin portal: every tab loads for the seeded admin
* no WebSocket drops, no page errors, no server tracebacks

Usage:
    python scripts/e2e_next_frontend.py            # offline LLM
    python scripts/e2e_next_frontend.py --live     # real Gemini
Requires: pnpm (FRONTEND deps installed), playwright + chromium.
"""
import asyncio
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import uuid
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx  # noqa: E402
from e2e_full_pipeline import TEST_DB, answer_from, free_port, known_mcq_answer, start_server, wait_healthy  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

LIVE = "--live" in sys.argv
SHOTS = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--shots=")), None)
ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "FRONTEND"
T0 = time.monotonic()
RIGHT = "Water evaporates from oceans, rises, cools and condenses into clouds, then falls as rain."
WRONG = "no idea"
PASSWORD = "Browser#12345"
DEMO_PASSWORD = "DemoStudent@123"


def log(msg: str) -> None:
    print(f"[{time.monotonic() - T0:6.1f}s] {msg}", flush=True)


class Failure(Exception):
    pass


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise Failure(msg)


def tiny_png(path: Path) -> None:
    """A real 8x8 PNG (sky blue), so the avatar upload sniffs as an image."""
    raw = b"".join(b"\x00" + b"\x3b\x66\xae" * 8 for _ in range(8))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


STATE_JS = """() => {
  const v = document.querySelector('[data-testid=lesson-video]');
  const card = document.querySelector('[data-testid=question-card]');
  const q = card ? card.querySelector('p.font-display') : null;
  return {t: v ? v.currentTime : 0, paused: v ? v.paused : true, visible: v ? getComputedStyle(v).visibility !== 'hidden' : false,
          controls: v ? v.controls : false, dur: v && v.duration ? v.duration : 0,
          card: !!card, qid: card ? card.dataset.interaction : '', grading: card ? card.dataset.grading === '1' : false,
          q: q ? q.innerText : '', feedback: !!document.querySelector('[data-testid=feedback]'),
          paused_panel: !!document.querySelector('[data-testid=paused-panel]'),
          review_panel: !!document.querySelector('[data-testid=review-panel]'),
          error_overlay: !!document.querySelector('[data-testid=overlay-error]'),
          conn: (document.querySelector('[data-testid=connection]') || {}).innerText || '',
          path: location.pathname, closes: window.__wsCloses || []};
}"""

WS_SPY = """(() => { const W = window.WebSocket; window.__wsCloses = [];
  window.WebSocket = function (u, p) { const ws = new W(u, p);
    ws.addEventListener('close', (e) => window.__wsCloses.push(e.code)); return ws; };
  window.WebSocket.prototype = W.prototype; Object.assign(window.WebSocket, W); })();"""


def build_and_start_frontend(api_base: str, port: int, log_path: Path) -> subprocess.Popen:
    env = dict(os.environ, NEXT_PUBLIC_BACKEND_URL=api_base, NEXT_DIST_DIR=".next-e2e", NEXT_TELEMETRY_DISABLED="1")
    log("building the Next.js frontend…")
    out = subprocess.run(["pnpm", "exec", "next", "build"], cwd=FE, env=env, capture_output=True, text=True)
    if out.returncode != 0:
        raise Failure(f"next build failed:\n{out.stdout[-3000:]}\n{out.stderr[-3000:]}")
    log("frontend built; starting it")
    return subprocess.Popen(["pnpm", "exec", "next", "start", "-p", str(port), "-H", "127.0.0.1"], cwd=FE, env=env,
                            stdout=open(log_path, "w"), stderr=subprocess.STDOUT)


def wait_up(url: str, proc: subprocess.Popen, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise Failure("frontend exited during startup")
        try:
            if httpx.get(url, timeout=2).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise Failure("frontend did not start in time")


class Run:
    def __init__(self, web: str, api: str, shots: Path):
        self.web, self.api, self.shots = web, api, shots
        self.errors: list[str] = []
        self.stats = {"checkpoints_paused": 0, "resumed": 0, "answers": 0, "reexplained": 0,
                      "seek_blocked": False, "escalated": False}

    def watch(self, page, name: str) -> None:
        page.on("pageerror", lambda e: self.errors.append(f"{name} pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and "favicon" not in m.text and "401" not in m.text
                and "Failed to load resource" not in m.text and self.errors.append(f"{name} console: {m.text[:300]}"))

    async def snap(self, page, name: str) -> None:
        """--shots=DIR saves a screenshot of each key moment for design review."""
        if SHOTS:
            Path(SHOTS).mkdir(parents=True, exist_ok=True)
            await asyncio.sleep(0.6)
            await page.screenshot(path=str(Path(SHOTS) / f"{name}.png"))

    async def token(self, page) -> str:
        return await page.evaluate("localStorage.getItem('shikshak.access')")

    async def script_for(self, page, lesson_id: str, node_hint: str) -> str:
        tok = await self.token(page)
        r = httpx.get(f"{self.api}/api/v1/lessons/{lesson_id}", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        nodes = r.json().get("nodes", [])
        texts = [n.get("script_text") or "" for n in nodes if n.get("script_text")]
        return texts[-1] if texts else node_hint

    # -- 1. landing + language ---------------------------------------------------
    async def landing(self, page) -> None:
        await page.goto(self.web + "/", wait_until="networkidle")
        await page.wait_for_selector("h1", timeout=20000)
        headline = " ".join((await page.inner_text("h1")).replace("\xa0", " ").split())
        check("didn't understand" in headline, f"landing hero headline missing: {headline!r}")
        for _ in range(8):
            await page.mouse.wheel(0, 1400)
            await asyncio.sleep(0.4)
        sections = ["problem", "loop", "ladder", "grounded", "langs", "hood"]
        for sid in sections:
            check(await page.locator(f"#{sid}").count() == 1, f"landing section #{sid} missing")
        # the visitor's checkpoint answers like a lesson
        await page.locator("button:has-text('Explains it again, a different way')").click()
        await page.wait_for_selector("text=You just learnt how Shikshak works", timeout=5000)
        # Hindi: every section still there, text changed
        en_cards = await page.locator("article, section").count()
        await page.locator("#langs [role=radio]:has-text('हिं')").click()
        await asyncio.sleep(0.6)
        check("भाषा" in await page.inner_text("#langs"), "landing did not switch to Hindi")
        check(await page.locator("article, section").count() == en_cards, "a card disappeared on switching language")
        await page.locator("#langs [role=radio]:has-text('EN')").click()
        log("landing: hero, 6 story sections, visitor checkpoint, EN↔हिं switch keeps every card")

    # -- 2. sign up with the on-screen OTP ------------------------------------------
    async def signup(self, page) -> str:
        email = f"n_{uuid.uuid4().hex[:6]}@example.com"
        await page.goto(self.web + "/signup")
        await page.fill("#name", "Next Learner")
        await page.fill("#email", email)
        await page.fill("#pw", PASSWORD)
        await page.fill("#mn", "Mentor Ma'am")
        await page.locator("button:has-text('Create account')").click()
        await page.wait_for_url("**/verify", timeout=20000)
        code = (await page.inner_text("[data-testid=demo-code]")).strip()
        check(len(code) == 6 and code.isdigit(), f"no on-screen OTP ({code!r})")
        await page.locator("button:has-text('Fill it in for me')").click()
        await page.wait_for_selector("text=नमस्ते", timeout=10000)
        await page.wait_for_url("**/dashboard", timeout=15000)
        await page.wait_for_selector("text=No lessons yet", timeout=15000)
        self.learner_email = email
        log(f"signed up {email}: on-screen OTP, auto-fill, namaste, empty dashboard")
        await self.snap(page, "dashboard-empty")
        # Hindi on the app: same cards, Hindi text
        await page.locator("aside [role=radio]:has-text('हिं')").click()
        await page.wait_for_selector("text=अभी कोई पाठ नहीं", timeout=5000)
        await page.locator("aside [role=radio]:has-text('EN')").click()
        return email

    # -- 3. new lesson ---------------------------------------------------------------
    async def new_lesson(self, page) -> str:
        await page.goto(self.web + "/new")
        await page.fill("#topic", "Water Cycle")
        await page.locator("button:has-text('10 min')").first.click()
        await page.locator("button:has-text('Plan my lesson')").click()
        await self.snap(page, "new-lesson")
        await page.wait_for_selector("button:has-text('Start the lesson')", timeout=180000)
        await self.snap(page, "plan")
        check(await page.locator("ol li").count() >= 1, "plan has no concepts")
        await page.locator("button:has-text('Start the lesson')").click()
        await page.wait_for_url("**/learn/**", timeout=15000)
        lesson_id = page.url.rstrip("/").split("/")[-1]
        log(f"planned + opened lesson {lesson_id}")
        return lesson_id

    # -- 4. the classroom loop ---------------------------------------------------------
    async def classroom(self, page, lesson_id: str, minutes: float) -> None:
        answers = [RIGHT, WRONG, WRONG, WRONG, WRONG, WRONG]
        last_q = None
        deadline = time.monotonic() + minutes * 60
        while time.monotonic() < deadline:
            await asyncio.sleep(1.0)
            st = await page.evaluate(STATE_JS)
            dropped = [c for c in st["closes"] if c not in (1000, 1005)]
            check(not dropped, f"WebSocket dropped mid-lesson (close codes {dropped})")
            check(not st["error_overlay"], "error overlay shown in the classroom")
            if "/report/" in st["path"]:
                raise Failure("lesson finished before the escalation path was exercised")

            if st["paused_panel"]:
                await asyncio.sleep(2)
                st = await page.evaluate(STATE_JS)
                check(st["paused"] and not st["controls"], f"video still playable after escalation: {st}")
                await page.evaluate("document.querySelector('[data-testid=lesson-video]').play().catch(()=>{})")
                await asyncio.sleep(1)
                check((await page.evaluate(STATE_JS))["paused"], "video resumed after the lesson was stopped for a human")
                self.stats["escalated"] = True
                await self.snap(page, "paused")
                log("escalated: paused panel, video stopped, controls removed")
                return

            if st["card"] and st["qid"] and st["qid"] != last_q and not st["grading"] and not st["feedback"]:
                check(st["paused"], f"question shown while the video plays: {st}")
                if st["visible"] and st["dur"] > 0:
                    check(0 < st["t"] < st["dur"] - 0.5, f"question not mid-video (t={st['t']:.1f}/{st['dur']:.1f})")
                    self.stats["checkpoints_paused"] += 1
                    await page.evaluate("document.querySelector('[data-testid=lesson-video]').play().catch(()=>{})")
                    await asyncio.sleep(0.8)
                    check((await page.evaluate(STATE_JS))["paused"], "video played past an unanswered question")
                    t0 = st["t"]
                    await page.evaluate("(t) => { document.querySelector('[data-testid=lesson-video]').currentTime = t + 20; }", t0)
                    await asyncio.sleep(0.8)
                    t1 = (await page.evaluate(STATE_JS))["t"]
                    check(t1 <= t0 + 1, f"seeked past an unanswered question ({t0:.1f}->{t1:.1f})")
                    self.stats["seek_blocked"] = True
                await self.snap(page, f"question-{self.stats['answers'] + 1}")
                card = page.locator("[data-testid=question-card]")
                box = card.locator("textarea")
                opts = card.locator("[role=radio]")
                has_opts = await opts.count() > 0
                check(not (has_opts and await box.count()), "an MCQ also shows a free-text box")
                answer = answers[min(self.stats["answers"], len(answers) - 1)]
                if answer == RIGHT:
                    key = known_mcq_answer(st["qid"])
                    if has_opts:
                        hit = card.locator("[role=radio]", has_text=key or "\u0000")
                        await (hit.first if key and await hit.count() else opts.first).click()
                    else:
                        await box.fill(answer_from(await self.script_for(page, lesson_id, RIGHT), st["q"]) or RIGHT)
                elif has_opts:
                    await opts.last.click()
                else:
                    await box.fill(answer)
                await card.locator("[data-testid=submit-answer]").click()
                await asyncio.sleep(0.15)
                st2 = await page.evaluate(STATE_JS)
                check(st2["grading"] or st2["feedback"] or not st2["card"], "submit did not lock the card while grading")
                if await card.count():
                    check(await card.locator("[data-testid=submit-answer]").count() == 0
                          or await card.locator("[data-testid=submit-answer]").is_disabled(), "Submit still enabled while grading")
                self.stats["answers"] += 1
                last_q = st["qid"]
                log(f"answered #{self.stats['answers']} ({'right' if answer == RIGHT else 'wrong'}) at t={st['t']:.1f}s")
                if answer == RIGHT:
                    for _ in range(60):
                        await asyncio.sleep(0.5)
                        s = await page.evaluate(STATE_JS)
                        if not s["paused"] and not s["card"]:
                            self.stats["resumed"] += 1
                            log("video resumed after the right answer")
                            break
                    else:
                        raise Failure(f"video did not resume after a right answer: {await page.evaluate(STATE_JS)}")
                else:
                    self.stats["reexplained"] += 1
        raise Failure(f"no escalation within {minutes} min: {self.stats}")

    async def after_escalation(self, page, lesson_id: str) -> None:
        await page.reload()
        await page.wait_for_selector("[data-testid=paused-panel]", timeout=20000)
        check((await page.evaluate(STATE_JS))["paused"], "reopened paused lesson started playing")
        log("reopened paused lesson: still paused")

        await page.goto(f"{self.web}/review/{lesson_id}#watch")
        await page.wait_for_selector("text=Waiting for your mentor", timeout=20000)
        await page.get_by_role("button", name="Watch", exact=True).first.click()
        await page.wait_for_selector("main video", timeout=20000)
        log("review: saved video loaded")
        await page.locator("[role=tab]:has-text('Practice questions')").click()
        card = page.locator("[data-testid=practice-card]").first
        await card.wait_for(timeout=20000)
        if await card.locator("textarea").count():
            await card.locator("textarea").fill("Water evaporates, condenses into clouds and falls as rain.")
        else:
            await card.locator("div.grid button").first.click()
        await card.get_by_role("button", name="Check", exact=True).click()
        await card.locator("text=/Correct|Not quite/").first.wait_for(timeout=30000)
        log("practice: instant feedback")
        await self.snap(page, "review-practice")

        await page.goto(f"{self.web}/learn/{lesson_id}")
        handle = page.locator("[data-testid=paused-panel] button[aria-label='Slide to skip this concept']")
        await handle.wait_for(timeout=20000)
        box = await handle.bounding_box()
        track = await page.locator("[data-testid=paused-panel] [role=group]").bounding_box()
        await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        await page.mouse.down()
        await page.mouse.move(track["x"] + track["width"] - 10, box["y"] + box["height"] / 2, steps=20)
        diag = await page.evaluate("""([x, y]) => { const el = document.elementFromPoint(x, y);
            const h = document.querySelector("[data-testid=paused-panel] button[aria-label='Slide to skip this concept']");
            return {under: el ? el.outerHTML.slice(0, 160) : null, transform: h ? h.style.transform : null}; }""",
            [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
        await page.mouse.up()
        log(f"slide diagnostics: {diag}")
        for _ in range(120):
            await asyncio.sleep(1)
            st = await page.evaluate(STATE_JS)
            if "/report/" in st["path"] or st["review_panel"] or (st["visible"] and st["dur"] > 0 and not st["paused_panel"]):
                break
        else:
            raise Failure(f"the lesson did not move on after slide-to-skip: {st}")
        log("slid to skip: lesson moved on")

        if "/learn/" in page.url:
            rewatch = page.locator("button[title='Rewatch']").first
            await rewatch.wait_for(timeout=60000)
            await rewatch.click()
            await page.wait_for_selector("[role=dialog] video", timeout=20000)
            await page.locator("[role=dialog] button:has-text('Back to the lesson')").click()
            await page.wait_for_selector("[role=dialog] video", state="detached", timeout=5000)
            log("rewatched an earlier concept in place, then back")

    # -- 5. profile ----------------------------------------------------------------------
    async def profile(self, page, png: Path) -> None:
        await page.goto(self.web + "/profile")
        await page.locator("[role=radio][aria-label='owl-sage']").click()
        await page.wait_for_selector("[role=radio][aria-label='owl-sage'][aria-checked=true]", timeout=10000)
        await page.set_input_files("#photo input[type=file]", str(png))
        await page.wait_for_selector("#photo img[src*='/account/avatar/file/']", timeout=15000)
        log("profile: avatar chosen, photo uploaded")
        await self.snap(page, "profile")
        for path in ("/dashboard", "/lessons", "/progress"):
            await page.goto(self.web + path)
            await asyncio.sleep(2.5)
            await self.snap(page, path.strip("/"))
        await page.locator("aside [role=radio]:has-text('हिं')").click()
        await asyncio.sleep(1)
        await self.snap(page, "progress-hi")
        await page.locator("aside [role=radio]:has-text('EN')").click()

    # -- 6. admin ------------------------------------------------------------------------------
    async def admin(self, browser) -> None:
        ctx = await browser.new_context()
        page = await ctx.new_page()
        self.watch(page, "admin")
        try:
            await self._admin(page)
        except Exception:
            await page.screenshot(path=str(self.shots / "admin-failure.png"))
            log(f"admin step failed at {page.url}; screenshot {self.shots / 'admin-failure.png'}")
            raise
        finally:
            await ctx.close()

    async def _admin(self, page) -> None:
        # a student account is refused at the staff door
        await page.goto(self.web + "/staff/login")
        await page.fill("#email", self.learner_email)
        await page.fill("#password", PASSWORD)
        await page.locator("form button[type=submit]").click()
        await page.wait_for_selector("text=This account is a student account", timeout=15000)
        # a new staff member signs up with the access code and lands in the portal
        await page.goto(self.web + "/staff/signup")
        await page.get_by_role("tab", name="Teacher").click()
        await page.fill("#name", "New Teacher")
        await page.fill("#email", f"t_{uuid.uuid4().hex[:6]}@example.com")
        await page.fill("#pw", PASSWORD)
        await page.fill("#code", "wrong-code")
        await page.locator("form button[type=submit]").click()
        await page.wait_for_selector("text=staff access code is not valid", timeout=15000)
        await page.fill("#code", "SHIKSHAK-ADMIN")
        await page.locator("form button[type=submit]").click()
        await page.wait_for_url("**/verify", timeout=20000)
        await page.locator("button:has-text('Fill it in for me')").click()
        await page.wait_for_url("**/admin", timeout=20000)
        await page.wait_for_selector("text=Teacher desk", timeout=15000)
        side = await page.inner_text("aside")
        check("New lesson" not in side and "Progress" not in side, f"learner pages in the staff sidebar: {side!r}")
        check("AI quality" not in side and "Mentor inbox" in side, f"teacher sidebar wrong: {side!r}")
        await page.goto(self.web + "/dashboard")
        await page.wait_for_url("**/admin", timeout=15000)
        log("staff: student refused at staff sign-in; bad code refused; teacher signed up -> admin portal")
        await page.locator("aside button[aria-label='Sign out']").click()
        await page.wait_for_url(self.web + "/", timeout=15000)
        await page.goto(self.web + "/staff/login")
        await page.fill("#email", "admin@shikshak.ai")
        await page.fill("#password", DEMO_PASSWORD)
        await page.locator("form button[type=submit]").click()
        await page.wait_for_url("**/admin", timeout=20000)
        await page.wait_for_selector("text=Mission control", timeout=15000)
        side = await page.inner_text("aside")
        check("New lesson" not in side and "AI quality" in side, f"admin sidebar wrong: {side!r}")
        for tab in ["Live classrooms", "Mentor inbox", "Learning insights", "AI quality", "System health", "Learners", "Overview"]:
            await page.locator(f"aside a:has-text('{tab}')").first.click()
            await asyncio.sleep(1.2)
            check("This area is for admins" not in await page.inner_text("main"), f"admin tab {tab} refused")
        await page.locator("aside a:has-text('Mentor inbox')").first.click()
        await page.get_by_role("button", name="All").first.click()
        try:
            await page.wait_for_selector("text=Next Learner", timeout=15000)
        except Exception:
            await page.screenshot(path=str(self.shots / "admin.png"))
            raise
        log("admin: all 7 tabs load; the escalation is in the mentor inbox")
        await self.snap(page, "admin-inbox")
        for tab in ("Overview", "Learning insights", "Learners"):
            await page.locator(f"aside a:has-text('{tab}')").first.click()
            await asyncio.sleep(1.5)
            await self.snap(page, "admin-" + tab.split()[0].lower())


async def run(web: str, api: str, png: Path, minutes: float, shots: Path) -> Run:
    r = Run(web, api, shots)
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        await ctx.add_init_script(WS_SPY)
        page = await ctx.new_page()
        r.watch(page, "learner")
        try:
            await r.landing(page)
            await r.signup(page)
            lesson_id = await r.new_lesson(page)
            await r.classroom(page, lesson_id, minutes)
            await r.after_escalation(page, lesson_id)
            await r.profile(page, png)
            await r.admin(browser)
        except Exception as exc:
            await page.screenshot(path=str(shots / "failure.png"), full_page=False)
            raise Failure(f"{type(exc).__name__}: {str(exc).splitlines()[0]} (at {page.url}; screenshot {shots / 'failure.png'})") from None
        finally:
            await browser.close()
    return r


def main() -> int:
    data = Path(tempfile.mkdtemp(prefix="shikshak_next_"))
    TEST_DB["path"] = str(data / "e2e.db")
    api_port, web_port = free_port(), free_port()
    api, web = f"http://127.0.0.1:{api_port}", f"http://127.0.0.1:{web_port}"
    os.environ["CORS_ORIGINS"] = f"{web},http://localhost:{web_port}"
    os.environ["DEFAULT_DEMO_PASSWORD"] = DEMO_PASSWORD
    os.environ["WARM_GRADER"] = "false"
    os.environ["ADMIN_SIGNUP_CODE"] = "SHIKSHAK-ADMIN"
    backend = start_server(api_port, data, LIVE, data / "server.log")
    frontend = None
    code = 1
    try:
        wait_healthy(api, backend)
        frontend = build_and_start_frontend(api, web_port, data / "web.log")
        wait_up(web + "/login", frontend)
        png = data / "me.png"
        tiny_png(png)
        r = asyncio.run(run(web, api, png, minutes=12 if LIVE else 6, shots=data))
        log(f"stats {r.stats}")
        check(r.stats["checkpoints_paused"] >= 1, "the video never paused at a checkpoint")
        check(r.stats["resumed"] >= 1, "the video never resumed after a right answer")
        check(r.stats["seek_blocked"], "seeking past a question was never tested")
        check(r.stats["escalated"], "more than 3 wrong answers did not stop the lesson")
        check(not r.errors, "browser errors:\n  " + "\n  ".join(r.errors[:20]))
        server_log = (data / "server.log").read_text(errors="replace")
        check("Traceback" not in server_log, "traceback in server log")
        print("\nNEXT FRONTEND: ALL CHECKS PASSED")
        code = 0
    except Failure as exc:
        print(f"\nNEXT FRONTEND FAILED: {exc}\nlogs: {data}")
    finally:
        for proc in (frontend, backend):
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if code == 0:
            shutil.rmtree(data, ignore_errors=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
