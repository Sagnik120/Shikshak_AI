#!/usr/bin/env python3
"""Real-browser check of the classroom page (headless Chromium via Playwright).

Plays a lesson the way a learner does and asserts what the learner sees:

* the video PAUSES at each mid-video checkpoint and shows the question
* the video can't be played or seeked past an unanswered question
* a right answer resumes the same video; a wrong one re-explains
* more than 3 wrong answers stop the lesson: the video is paused, no controls
* the connection never drops (the server keeps reading the socket)

Usage:
    python scripts/e2e_browser_classroom.py            # offline LLM
    python scripts/e2e_browser_classroom.py --live     # real Gemini
Requires: pip install playwright && python -m playwright install chromium
"""
import asyncio
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx  # noqa: E402
from e2e_full_pipeline import TEST_DB, answer_from, free_port, known_mcq_answer, start_server, wait_healthy  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

LIVE = "--live" in sys.argv
T0 = time.monotonic()
RIGHT = "Water evaporates from oceans, rises, cools and condenses into clouds, then falls as rain."
WRONG = "no idea"


def log(msg: str) -> None:
    print(f"[{time.monotonic() - T0:6.1f}s] {msg}", flush=True)


class Failure(Exception):
    pass


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise Failure(msg)


STATE_JS = """() => {
  const v = document.querySelector('#video'), cp = document.querySelector('#checkpoint');
  return {t: v.currentTime, paused: v.paused, hidden: v.hidden, controls: v.controls,
          dur: v.duration || 0, card: !!cp && !cp.hidden,
          q: (document.querySelector('#question-text') || {}).innerText || '',
          qid: (cp && cp.dataset.interaction) || '',
          grading: (document.querySelector('#submit-answer') || {}).innerText || '',
          overlay: !document.querySelector('#overlay').hidden,
          badge: document.querySelector('#connection-badge').innerText,
          status: document.querySelector('#status-text').innerText,
          closes: window.__wsCloses || []};
}"""

WS_SPY = """(() => { const W = window.WebSocket; window.__wsCloses = [];
  window.WebSocket = function (u, p) { const ws = new W(u, p);
    ws.addEventListener('close', (e) => window.__wsCloses.push(e.code)); return ws; };
  window.WebSocket.prototype = W.prototype; Object.assign(window.WebSocket, W); })();"""


async def after_escalation(page, base: str, lesson_id: str, stats: dict) -> None:
    """The paused lesson, the review page, practice, then skipping on."""
    labels = await page.locator("#overlay-actions > *").all_inner_texts()
    check(len(labels) == 3 and any("Continue" in x for x in labels) and any("Skip" in x for x in labels),
          f"paused panel actions: {labels}")

    # Reopening a paused lesson must show the pause, never start teaching.
    await page.reload()
    await asyncio.sleep(3)
    check("mentor" in (await page.inner_text("#overlay")).lower(), "reopened paused lesson did not show the pause")
    check((await page.evaluate("document.querySelector('#video').paused")), "paused lesson started playing")
    log("reopened paused lesson: still paused, nothing regenerated")

    # Review: saved videos play freely; practice gives instant feedback.
    await page.goto(f"{base}/review.html?lesson={lesson_id}#watch")
    await page.wait_for_selector("text=Watch again", timeout=15000)
    check("Waiting for your mentor" in await page.inner_text("#review-root"), "review page lacks the pause banner")
    watch = page.locator("#review-root .actions button:text-is('Watch')").first
    await watch.click()
    await page.wait_for_selector("#review-root video", timeout=15000)
    log("review: saved video loaded")
    await page.locator("button:has-text('Practice questions')").click()
    await page.wait_for_selector("text=Check answer", timeout=15000)
    card = page.locator("#review-root section.card").first
    if await card.locator("textarea").count():
        await card.locator("textarea").fill("Water evaporates, condenses into clouds and falls as rain.")
    else:
        await card.locator(".option").first.click()
    await card.locator("button:has-text('Check answer')").click()
    await page.wait_for_selector("#review-root .result.feedback", timeout=30000)
    log("practice: answered with instant feedback")
    stats["reviewed"] = True

    # Skip the stuck concept: the lesson carries on (or finishes) cleanly.
    await page.goto(f"{base}/classroom.html?lesson={lesson_id}")
    await page.wait_for_selector("#overlay-actions button:has-text('Skip')", timeout=15000)
    await page.locator("#overlay-actions button:has-text('Skip')").click()
    for _ in range(90):
        await asyncio.sleep(1)
        if "report.html" in page.url:
            break
        st = await page.evaluate(STATE_JS)
        if not st["hidden"] and st["dur"] > 0:
            break
    check("report.html" in page.url or not (await page.evaluate(STATE_JS))["hidden"],
          "the lesson did not continue after skipping")
    stats["skipped_on"] = True
    log("skipped the concept: lesson continued")

    # The skipped concept reads "To review" and can be rewatched in place.
    await page.goto(f"{base}/classroom.html?lesson={lesson_id}")
    await page.wait_for_selector(".node-item[data-rewatch]", timeout=60000)
    rail = await page.inner_text("#node-list")
    check("To review" in rail, f"skipped concept not shown as 'To review': {rail!r}")
    href = await page.get_attribute("#practice-link", "href")
    check(href and "review.html" in href and "#practice" in href, f"no practice link in the classroom ({href})")
    await page.locator(".node-item[data-rewatch]").first.click()
    await page.wait_for_function(
        "() => !document.querySelector('#rewatch').hidden && !!document.querySelector('#rewatch-video').src",
        timeout=20000)
    await page.locator("#rewatch-close").click()
    await page.wait_for_function("() => document.querySelector('#rewatch').hidden", timeout=5000)
    check(not await page.evaluate("!!document.querySelector('#rewatch-video').getAttribute('src')"),
          "rewatch video kept playing after closing")
    stats["rewatched"] = True
    log("rewatched the skipped concept from the side list, then back to the lesson")


async def run(base: str, token: dict, lesson_id: str, minutes: float) -> dict:
    stats = {"checkpoints_paused": 0, "resumed": 0, "answers": 0, "escalated": False,
             "seek_blocked": False, "reexplained": 0}
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        page = await browser.new_page()
        page.on("pageerror", lambda e: log(f"PAGE ERROR {e}"))
        await page.add_init_script(WS_SPY)
        await page.goto(base + "/login.html")
        await page.evaluate("""(t) => { localStorage.setItem('shikshak.access', t.access_token);
            localStorage.setItem('shikshak.refresh', t.refresh_token);
            localStorage.setItem('shikshak.user', JSON.stringify(t.user)); }""", token)
        await page.goto(f"{base}/classroom.html?lesson={lesson_id}")

        answers = [RIGHT, WRONG, WRONG, WRONG, WRONG, WRONG]
        last_q = None
        deadline = time.monotonic() + minutes * 60
        while time.monotonic() < deadline:
            await asyncio.sleep(1.0)
            st = await page.evaluate(STATE_JS)
            dropped = [c for c in st["closes"] if c != 1000]  # 1000 = lesson ended normally
            check(not dropped, f"WebSocket dropped mid-lesson (close codes {dropped})")
            check("Something went wrong" not in (await page.inner_text("#overlay")), "error overlay shown")

            if "waiting for your mentor" in (await page.inner_text("#overlay")).lower():
                await asyncio.sleep(2)
                st = await page.evaluate(STATE_JS)
                check(st["paused"] and not st["controls"], f"video still playable after escalation: {st}")
                await page.evaluate("document.querySelector('#video').play().catch(()=>{})")
                await asyncio.sleep(1)
                st = await page.evaluate(STATE_JS)
                check(st["paused"], "video resumed after the lesson was stopped for a human")
                stats["escalated"] = True
                log("escalated: video stopped, controls removed")
                await after_escalation(page, base, lesson_id, stats)
                break

            if st["card"] and st["qid"] and st["qid"] != last_q and st["grading"] != "Grading…":
                # Question shown: the video must be paused and stay paused.
                check(st["paused"], f"question shown while the video plays: {st}")
                if not st["hidden"]:
                    check(0 < st["t"] < st["dur"] - 0.5, f"question not mid-video (t={st['t']:.1f}/{st['dur']:.1f})")
                    stats["checkpoints_paused"] += 1
                    await page.evaluate("document.querySelector('#video').play().catch(()=>{})")
                    await asyncio.sleep(0.8)
                    check((await page.evaluate(STATE_JS))["paused"], "video played past an unanswered question")
                    t_before = st["t"]
                    await page.evaluate("(t) => { const v = document.querySelector('#video'); v.currentTime = t + 20; }", t_before)
                    await asyncio.sleep(0.8)
                    t_after = (await page.evaluate(STATE_JS))["t"]
                    check(t_after <= t_before + 1, f"seeked past an unanswered question ({t_before:.1f}->{t_after:.1f})")
                    stats["seek_blocked"] = True
                answer = answers[min(stats["answers"], len(answers) - 1)]
                box = page.locator("#answer-input")
                has_options = await page.locator("#options .option").count() > 0
                check(not (has_options and await box.is_visible()),
                      "a multiple-choice question also shows the free-text box")
                if answer == RIGHT:
                    # A learner who knows it: the right option, or the narration's words.
                    key = known_mcq_answer(st["qid"])
                    transcript = await page.inner_text("#notes-transcript")
                    if await box.is_visible():
                        await box.fill(answer_from(transcript, st["q"]) or RIGHT)
                    else:
                        option = page.locator("#options .option", has_text=key or "")
                        await (option.first if key and await option.count() else page.locator("#options .option").first).click()
                elif await box.is_visible():
                    await box.fill(answer)
                else:
                    await page.locator("#options .option").last.click()
                await page.locator("#submit-answer").click()
                # A double-click must not send a second answer.
                check(await page.locator("#submit-answer").is_disabled(), "Submit still enabled while grading")
                await box.type(" more", delay=5) if await box.is_visible() else None
                check(await page.locator("#submit-answer").is_disabled(), "typing re-enabled Submit mid-grading")
                stats["answers"] += 1
                last_q = st["qid"]
                log(f"answered #{stats['answers']} ({'right' if answer == RIGHT else 'wrong'}) at t={st['t']:.1f}s")
                if answer == RIGHT:
                    for _ in range(60):  # up to 30 s: grading can be slow under rate limits
                        await asyncio.sleep(0.5)
                        s2 = await page.evaluate(STATE_JS)
                        if not s2["paused"] and not s2["card"]:
                            stats["resumed"] += 1
                            log("video resumed after the right answer")
                            break
                    else:
                        s3 = await page.evaluate(STATE_JS)
                        events = await page.inner_text("#event-log")
                        raise Failure(f"video did not resume after a right answer: {s3}\n--- page log ---\n{events[-1500:]}")
                else:
                    stats["reexplained"] += 1
        await browser.close()
    return stats


def main() -> int:
    data = Path(tempfile.mkdtemp(prefix="shikshak_browser_"))
    TEST_DB["path"] = str(data / "e2e.db")
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    proc = start_server(port, data, LIVE, data / "server.log")
    code = 1
    try:
        wait_healthy(base, proc)
        c = httpx.Client(base_url=base, timeout=120)
        email = f"b_{uuid.uuid4().hex[:6]}@example.com"
        otp = c.post("/api/v1/auth/signup", json={"full_name": "Browser Learner", "email": email,
                                                    "password": "Browser#12345"}).json()["dev_otp"]
        token = c.post("/api/v1/auth/verify-email", json={"email": email, "code": otp}).json()
        c.headers["Authorization"] = f"Bearer {token['access_token']}"
        r = c.post("/api/v1/lessons", json={"topic": "Water Cycle", "time_budget_min": 10})
        check(r.status_code == 201, f"create lesson right after verify: {r.status_code} {r.text}")
        lesson_id = r.json()["lesson_id"]
        check(c.post(f"/api/v1/lessons/{lesson_id}/plan").status_code == 200, "plan failed")

        stats = asyncio.run(run(base, token, lesson_id, minutes=12 if LIVE else 6))
        log(f"stats {stats}")
        check(stats["checkpoints_paused"] >= 1, "the video never paused at a checkpoint")
        check(stats["resumed"] >= 1, "the video never resumed after a right answer")
        check(stats["seek_blocked"], "seeking past a question was never tested")
        check(stats["escalated"], "more than 3 wrong answers did not stop the lesson")
        check(stats.get("reviewed"), "review & practice were not exercised")
        check(stats.get("skipped_on"), "skipping on after the pause was not exercised")
        check(stats.get("rewatched"), "rewatching an earlier concept was not exercised")
        log_text = (data / "server.log").read_text(errors="replace")
        check("Traceback" not in log_text, "traceback in server log")
        check("keepalive ping timeout" not in log_text, "server dropped a socket (keepalive timeout)")
        print("\nBROWSER CLASSROOM: ALL CHECKS PASSED")
        code = 0
    except Failure as exc:
        print(f"\nBROWSER CLASSROOM FAILED: {exc}\nserver log: {data / 'server.log'}")
    finally:
        proc.terminate()
        proc.wait(timeout=15)
        if code == 0:
            shutil.rmtree(data, ignore_errors=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
