/**
 * Review & practice: rewatch a lesson exactly as it was taught (saved videos
 * and notes — nothing is regenerated) and practise its questions. Nothing on
 * this page changes the lesson's score, progress or history; the only lesson
 * actions are the explicit Continue / Skip / Learn this again buttons.
 */
import { api } from "../api.js";
import {
  $, el, clear, escapeHtml, icon, toast, requireAuth, mountHeader, emptyState, lessonStatus,
} from "../ui.js";

const user = await requireAuth();
const params = new URLSearchParams(window.location.search);
const lessonId = params.get("lesson");

const NOTE_LABEL = {
  "after help": { text: "Mastered · after help", cls: "badge badge-green" },
  "after review": { text: "Mastered · after review", cls: "badge badge-green" },
  "needs review": { text: "Needs review", cls: "badge badge-amber" },
};
const STATUS_LABEL = {
  mastered: { text: "Mastered", cls: "badge badge-green" },
  completed: { text: "Watched", cls: "badge badge-green" },
  skipped: { text: "To review", cls: "badge badge-amber" },
  struggling: { text: "In progress", cls: "badge badge-amber" },
  teaching: { text: "In progress", cls: "badge badge-amber" },
  questioning: { text: "In progress", cls: "badge badge-amber" },
  pending: { text: "Not reached yet", cls: "badge" },
};
const TYPE_LABEL = {
  mcq: "Multiple choice",
  short_answer: "Short answer",
  problem: "Problem",
  application: "Apply it",
  explain_in_own_words: "In your own words",
};

if (user && !lessonId) {
  window.location.replace("/lessons.html");
} else if (user) {
  mountHeader(user, "/lessons.html");
  const root = $("#review-root");
  const objectUrls = [];
  let lesson = null;

  try {
    lesson = await api.getLesson(lessonId);
    render();
  } catch (error) {
    clear(root).append(
      emptyState("alert", "Couldn't load this lesson", error.message,
        el("a", { class: "btn btn-primary", href: "/lessons.html" }, "Back to my lessons"))
    );
  }

  window.addEventListener("beforeunload", () => objectUrls.forEach((u) => URL.revokeObjectURL(u)));

  function render() {
    clear(root);
    root.append(header());
    const paused = pausedBanner();
    if (paused) root.append(paused);

    const tabs = el("div", { class: "row", style: "gap:var(--sp-2);margin:var(--sp-5) 0 var(--sp-4)", role: "tablist" });
    const watchTab = el("button", { class: "btn btn-secondary", type: "button", role: "tab" }, "Watch again");
    const practiceTab = el("button", { class: "btn btn-secondary", type: "button", role: "tab" }, "Practice questions");
    tabs.append(watchTab, practiceTab);
    const panel = el("div");
    root.append(tabs, panel);

    const show = (which) => {
      watchTab.className = `btn ${which === "watch" ? "btn-primary" : "btn-secondary"}`;
      practiceTab.className = `btn ${which === "practice" ? "btn-primary" : "btn-secondary"}`;
      watchTab.setAttribute("aria-selected", String(which === "watch"));
      practiceTab.setAttribute("aria-selected", String(which === "practice"));
      clear(panel);
      if (which === "watch") panel.append(watchPanel());
      else practicePanel(panel);
      history.replaceState(null, "", which === "practice" ? "#practice" : "#watch");
    };
    watchTab.addEventListener("click", () => show("watch"));
    practiceTab.addEventListener("click", () => show("practice"));
    show(window.location.hash === "#practice" ? "practice" : "watch");
  }

  function header() {
    const status = lessonStatus(lesson);
    const node = el("div", { class: "row-between row-wrap page-head" });
    node.innerHTML = `
      <div>
        <a href="/lessons.html" class="row subtle" style="gap:6px;margin-bottom:8px;text-decoration:none">
          ${icon("arrowLeft", 15)} All lessons
        </a>
        <h1>${escapeHtml(lesson.title)}</h1>
        <p class="muted" style="margin-top:4px">
          <span class="${status.cls}">${escapeHtml(status.label)}</span>
          · ${lesson.nodes_completed} of ${lesson.node_count} concepts done
          · reviewing never changes your score
        </p>
      </div>
      <div class="row row-wrap" style="gap:var(--sp-2)">
        ${
          lesson.status === "completed"
            ? `<a class="btn btn-secondary" href="/report.html?lesson=${encodeURIComponent(lesson.id)}">Report</a>`
            : lesson.status !== "escalated"
            ? `<a class="btn btn-primary" href="/classroom.html?lesson=${encodeURIComponent(lesson.id)}">Resume lesson</a>`
            : ""
        }
      </div>`;
    return node;
  }

  /** Paused for a mentor: the two ways forward, on this page too. */
  function pausedBanner() {
    const esc = lesson.escalation;
    if (lesson.status !== "escalated" || !esc || esc.status !== "open") return null;
    const box = el("div", { class: "alert alert-warning", style: "margin-top:var(--sp-4)" });
    box.innerHTML = `
      <strong>Waiting for your mentor</strong>
      <div style="margin-top:4px">This lesson is paused at <strong>${escapeHtml(esc.concept)}</strong>.
      Review and practise here, or choose how to go on.</div>
      <div class="row row-wrap" style="gap:var(--sp-2);margin-top:var(--sp-3)">
        <button class="btn btn-primary btn-sm" type="button" data-act="continue">Continue — teach it again</button>
        <button class="btn btn-secondary btn-sm" type="button" data-act="skip">Skip this concept</button>
      </div>`;
    box.querySelector('[data-act="continue"]').addEventListener("click", (e) => lessonAction(e, "continue"));
    box.querySelector('[data-act="skip"]').addEventListener("click", (e) => lessonAction(e, "skip"));
    return box;
  }

  async function lessonAction(event, action, nodeId) {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      if (action === "continue") await api.continueLesson(lesson.id);
      else if (action === "skip") await api.skipConcept(lesson.id);
      else await api.relearnConcept(lesson.id, nodeId);
      window.location.href = `/classroom.html?lesson=${encodeURIComponent(lesson.id)}`;
    } catch (error) {
      toast(error.message, "error", 6000);
      button.disabled = false;
    }
  }

  /* -- Watch again ---------------------------------------------------------- */

  function watchPanel() {
    const wrap = el("div", { class: "stack", style: "--gap:var(--sp-4)" });
    const taught = lesson.nodes.filter((n) => n.script_text || n.video_url);
    if (!taught.length) {
      wrap.append(emptyState("play", "Nothing to rewatch yet",
        "Concepts appear here once they have been taught in the classroom."));
      return wrap;
    }
    const canRelearn = ["completed", "in_progress"].includes(lesson.status) && !lesson.relearning;

    lesson.nodes.forEach((node, index) => {
      if (!node.script_text && !node.video_url) return;
      const label = NOTE_LABEL[node.review_note] || STATUS_LABEL[node.status] || STATUS_LABEL.pending;
      const card = el("section", { class: "card card-pad" });
      const points = (node.notes?.key_points || []).map((p) => `<li>${escapeHtml(p)}</li>`).join("");
      card.innerHTML = `
        <div class="row-between row-wrap" style="gap:var(--sp-2)">
          <h3 style="margin:0">${index + 1}. ${escapeHtml(node.concept)}</h3>
          <span class="${label.cls}">${escapeHtml(label.text)}</span>
        </div>
        <div class="video-slot" style="margin-top:var(--sp-3)"></div>
        ${points ? `<ul style="margin:var(--sp-3) 0 0;padding-left:1.1rem;line-height:1.6">${points}</ul>` : ""}
        ${node.notes?.example ? `<p class="subtle" style="margin-top:6px">Example: ${escapeHtml(node.notes.example)}</p>` : ""}
        ${node.script_text ? `<details style="margin-top:var(--sp-3)"><summary style="cursor:pointer">Full transcript</summary>
          <p style="margin-top:var(--sp-2);line-height:1.7">${escapeHtml(node.script_text)}</p></details>` : ""}
        <div class="row row-wrap actions" style="gap:var(--sp-2);margin-top:var(--sp-3)"></div>`;

      const actions = card.querySelector(".actions");
      if (node.video_url) {
        const play = el("button", { class: "btn btn-secondary btn-sm", type: "button" }, "Watch");
        play.addEventListener("click", () => loadVideo(card.querySelector(".video-slot"), node, play));
        actions.append(play);
      }
      if (node.status === "skipped" && canRelearn) {
        const again = el("button", { class: "btn btn-primary btn-sm", type: "button" }, "Learn this again");
        again.addEventListener("click", (e) => lessonAction(e, "relearn", node.node_id));
        actions.append(again);
      }
      wrap.append(card);
    });
    return wrap;
  }

  async function loadVideo(slot, node, button) {
    button.disabled = true;
    try {
      const url = await api.mediaObjectUrl(node.video_url);
      objectUrls.push(url);
      clear(slot).append(el("video", {
        src: url, controls: true, playsinline: true, preload: "auto",
        style: "width:100%;border-radius:12px;background:#000",
      }));
      button.remove(); // free playback: no pauses, no questions, seek anywhere
    } catch (error) {
      toast(`Couldn't load the video: ${error.message}`, "error");
      button.disabled = false;
    }
  }

  /* -- Practice ------------------------------------------------------------- */

  async function practicePanel(panel) {
    panel.append(el("p", { class: "muted" }, "Loading your questions…"));
    let data;
    try {
      data = await api.practice(lesson.id);
    } catch (error) {
      clear(panel).append(emptyState("alert", "Couldn't load practice questions", error.message));
      return;
    }
    clear(panel);
    if (!data.questions.length) {
      panel.append(emptyState("check", "No questions yet",
        "Questions you answer in the lesson become practice questions here."));
      return;
    }
    const intro = el("p", { class: "muted", style: "margin-bottom:var(--sp-3)" },
      "Practise at your own pace. Answers here never change your lesson score.");
    const list = el("div", { class: "stack", style: "--gap:var(--sp-4)" });
    data.questions.forEach((q, i) => list.append(practiceCard(q, i)));
    panel.append(intro, list);
  }

  function practiceCard(q, index) {
    const card = el("section", { class: "card card-pad" });
    card.innerHTML = `
      <div class="row-between row-wrap" style="gap:var(--sp-2)">
        <span class="subtle">${index + 1}. ${escapeHtml(q.concept)} · ${escapeHtml(TYPE_LABEL[q.type] || "Question")}</span>
        ${q.needs_practice ? '<span class="badge badge-amber">Needs practice</span>' : ""}
      </div>
      <p style="font-weight:600;margin:var(--sp-2) 0 var(--sp-3)">${escapeHtml(q.question_text)}</p>
      <div class="answer"></div>
      <div class="row" style="gap:var(--sp-2);margin-top:var(--sp-3)">
        <button class="btn btn-primary btn-sm" type="button" disabled>Check answer</button>
      </div>
      <div class="result" style="margin-top:var(--sp-3)"></div>`;

    const answerBox = card.querySelector(".answer");
    const check = card.querySelector("button");
    let picked = null;
    let input = null;

    if (q.options.length) {
      q.options.forEach((option) => {
        const b = el("button", { class: "option", type: "button", "aria-pressed": "false" });
        b.innerHTML = `<span class="option-radio"></span><span>${escapeHtml(option)}</span>`;
        b.addEventListener("click", () => {
          picked = option;
          [...answerBox.children].forEach((c) => c.setAttribute("aria-pressed", String(c === b)));
          check.disabled = false;
        });
        answerBox.append(b);
      });
    } else {
      input = el("textarea", { rows: "3", class: "input", placeholder: "Answer in your own words", style: "width:100%" });
      input.addEventListener("input", () => { check.disabled = input.value.trim().length < 2; });
      answerBox.append(input);
    }

    check.addEventListener("click", async () => {
      const answer = picked ?? input?.value.trim();
      if (!answer) return;
      check.disabled = true;
      check.textContent = "Checking…";
      try {
        const r = await api.answerPractice(lesson.id, q.interaction_id, answer);
        const result = card.querySelector(".result");
        result.className = `result feedback ${r.correct ? "correct" : "incorrect"}`;
        result.innerHTML = `
          <div class="feedback-title">${icon(r.correct ? "check" : "alert", 16)} ${r.correct ? "Correct" : "Not quite"}</div>
          <div>${escapeHtml(r.feedback_text || "")}</div>
          ${r.correct ? "" : `<div style="margin-top:6px"><strong>Answer:</strong> ${escapeHtml(r.model_answer || "")}</div>`}`;
      } catch (error) {
        toast(error.message, "error");
      } finally {
        check.textContent = "Check again";
        check.disabled = false;
      }
    });
    return card;
  }
}
