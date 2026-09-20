/** Lesson report: score, concept timeline, answers given, rewatchable video. */
import { api } from "../api.js";
import {
  $, el, clear, escapeHtml, icon, toast, requireAuth, mountHeader,
  formatDate, formatDuration, formatSeconds, emptyState, scoreClass, LEVEL_LABELS,
} from "../ui.js";

const user = await requireAuth();
const lessonId = new URLSearchParams(window.location.search).get("lesson");

if (user && !lessonId) {
  window.location.replace("/lessons.html");
} else if (user) {
  mountHeader(user, "/lessons.html");
  const root = $("#report-root");

  try {
    render(await api.getLesson(lessonId));
  } catch (error) {
    clear(root).append(
      emptyState("alert", "Couldn't load this report", error.message,
        el("a", { class: "btn btn-primary", href: "/lessons.html" }, "Back to my lessons"))
    );
  }

  function render(lesson) {
    clear(root);
    root.append(header(lesson), summary(lesson));

    if (lesson.report) root.append(narrative(lesson.report));
    root.append(timeline(lesson));
  }

  function header(lesson) {
    const node = el("div", { class: "row-between row-wrap page-head" });
    node.innerHTML = `
      <div>
        <a href="/lessons.html" class="row subtle" style="gap:6px;margin-bottom:8px;text-decoration:none">
          ${icon("arrowLeft", 15)} All lessons
        </a>
        <h1>${escapeHtml(lesson.title)}</h1>
        <p class="muted" style="margin-top:4px">
          ${escapeHtml(LEVEL_LABELS[lesson.level] || lesson.level)} ·
          ${lesson.node_count} concepts ·
          ${escapeHtml(formatDuration(lesson.watch_minutes))} of teaching ·
          ${lesson.completed_at ? `completed ${escapeHtml(formatDate(lesson.completed_at))}` : "in progress"}
        </p>
      </div>
      ${
        lesson.status !== "completed"
          ? `<a class="btn btn-primary" href="/classroom.html?lesson=${encodeURIComponent(
              lesson.id
            )}">Resume lesson</a>`
          : `<a class="btn btn-secondary" href="/new-lesson.html">Study something new</a>`
      }`;
    return node;
  }

  function summary(lesson) {
    const score = lesson.report?.score_pct ?? lesson.progress_pct;
    const mastered = lesson.nodes.filter((n) => n.status === "mastered").length;
    const questions = lesson.nodes.reduce((sum, n) => sum + n.interactions.length, 0);
    const correct = lesson.nodes.reduce(
      (sum, n) => sum + n.interactions.filter((i) => i.correct).length,
      0
    );
    const reexplains = lesson.nodes.reduce((sum, n) => sum + n.times_reexplained, 0);

    const card = el("section", { class: "card card-pad", style: "margin-bottom:var(--sp-5)" });
    card.innerHTML = `
      <div class="grid" style="grid-template-columns:auto 1fr;gap:var(--sp-8);align-items:center">
        <div class="score-ring">
          ${ring(score)}
          <span class="score-ring-value" style="color:var(--${ringColor(score)})">${Math.round(score)}%</span>
        </div>
        <div class="stat-grid" style="grid-template-columns:repeat(2,1fr)">
          <div class="stat" style="border:0;padding:0;background:none">
            <div class="stat-label">Concepts mastered</div>
            <div class="stat-value" style="font-size:var(--text-2xl)">${mastered}<span class="subtle" style="font-size:var(--text-md)"> / ${lesson.node_count}</span></div>
          </div>
          <div class="stat" style="border:0;padding:0;background:none">
            <div class="stat-label">Questions correct</div>
            <div class="stat-value" style="font-size:var(--text-2xl)">${correct}<span class="subtle" style="font-size:var(--text-md)"> / ${questions}</span></div>
          </div>
          <div class="stat" style="border:0;padding:0;background:none">
            <div class="stat-label">Time taught</div>
            <div class="stat-value" style="font-size:var(--text-2xl)">${escapeHtml(formatDuration(lesson.watch_minutes))}</div>
          </div>
          <div class="stat" style="border:0;padding:0;background:none">
            <div class="stat-label">Re-explanations</div>
            <div class="stat-value" style="font-size:var(--text-2xl)">${reexplains}</div>
            <div class="stat-meta">${reexplains ? "concepts taught a second way" : "first pass was enough"}</div>
          </div>
        </div>
      </div>`;
    return card;
  }

  function ring(score) {
    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - Math.min(100, Math.max(0, score)) / 100);
    return `<svg width="132" height="132" viewBox="0 0 132 132" aria-hidden="true">
      <circle cx="66" cy="66" r="${radius}" fill="none" stroke="var(--bg-sunken)" stroke-width="11"/>
      <circle cx="66" cy="66" r="${radius}" fill="none" stroke="var(--${ringColor(score)})"
              stroke-width="11" stroke-linecap="round"
              stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"/>
    </svg>`;
  }

  function ringColor(score) {
    const cls = scoreClass(score);
    return cls === "high" ? "green-600" : cls === "mid" ? "amber-500" : "rose-600";
  }

  function narrative(report) {
    const card = el("section", { class: "card", style: "margin-bottom:var(--sp-5)" });
    card.innerHTML = `
      <div class="card-header"><h2 class="card-title">What Shikshak observed</h2></div>
      <div class="card-body stack" style="--gap:var(--sp-5)">
        <p style="line-height:1.7">${escapeHtml(report.narrative_feedback || "No written feedback for this lesson.")}</p>
        <div class="grid grid-3">
          ${column("Strong areas", report.strong_areas, "chip-strong")}
          ${column("Needs review", report.weak_areas, "chip-weak")}
          ${column("Recommended next", report.recommended_next, "")}
        </div>
      </div>`;
    return card;
  }

  function column(label, items, cls) {
    return `<div>
      <div class="section-label" style="margin-bottom:var(--sp-2)">${escapeHtml(label)}</div>
      ${
        items?.length
          ? `<div class="chip-cloud">${items
              .map((i) => `<span class="chip ${cls}">${escapeHtml(i)}</span>`)
              .join("")}</div>`
          : `<p class="subtle">None recorded.</p>`
      }
    </div>`;
  }

  function timeline(lesson) {
    const card = el("section", { class: "card" });
    card.innerHTML = `<div class="card-header"><h2 class="card-title">Concept by concept</h2>
      <span class="subtle">Every answer you gave</span></div>`;

    const body = el("div", { class: "card-body" });

    lesson.nodes.forEach((node, index) => {
      const item = el("div", { class: "timeline-item" });
      const markerClass =
        node.status === "mastered" ? "mastered" : node.status === "struggling" ? "struggling" : "";

      const content = el("div", { class: "grow" });
      content.innerHTML = `
        <div class="row-between row-wrap" style="align-items:flex-start">
          <div class="grow">
            <div style="font-weight:650">${escapeHtml(node.concept)}</div>
            <div class="lesson-row-meta">
              <span class="badge">${escapeHtml(node.depth)}</span>
              <span>${escapeHtml(node.status.replace("_", " "))}</span>
              ${node.attempts ? `<span>${node.attempts} attempt${node.attempts === 1 ? "" : "s"}</span>` : ""}
              ${node.times_reexplained ? `<span>re-taught ${node.times_reexplained}×</span>` : ""}
              ${node.duration_sec ? `<span>${escapeHtml(formatSeconds(node.duration_sec))} of video</span>` : ""}
            </div>
          </div>
          ${
            node.video_url
              ? `<button class="btn btn-secondary btn-sm" data-video="${escapeHtml(node.video_url)}">
                   ${icon("play", 14)} Rewatch</button>`
              : ""
          }
        </div>`;

      if (node.script_text) {
        const script = el("details", { style: "margin-top:var(--sp-3)" });
        script.innerHTML = `<summary class="subtle" style="cursor:pointer">What the teacher said</summary>
          <p style="font-size:var(--text-sm);line-height:1.65;margin-top:var(--sp-2);color:var(--text-muted)">${escapeHtml(
            node.script_text
          )}</p>`;
        content.append(script);
      }

      node.interactions.forEach((qa) => content.append(interaction(qa)));

      const videoHost = el("div", { style: "margin-top:var(--sp-3)" });
      content.append(videoHost);

      const rewatch = $("[data-video]", content);
      rewatch?.addEventListener("click", async () => {
        rewatch.disabled = true;
        rewatch.textContent = "Loading…";
        try {
          const url = await api.mediaObjectUrl(node.video_url);
          clear(videoHost).append(
            el("video", {
              src: url,
              controls: true,
              playsinline: true,
              style: "width:100%;max-width:640px;border-radius:var(--radius);background:#06080f",
            })
          );
          rewatch.remove();
        } catch (error) {
          toast(error.message, "error");
          rewatch.disabled = false;
          rewatch.innerHTML = `${icon("play", 14)} Rewatch`;
        }
      });

      item.innerHTML = `<span class="timeline-marker ${markerClass}">${
        node.status === "mastered" ? icon("check", 14) : index + 1
      }</span>`;
      item.append(content);
      body.append(item);
    });

    card.append(body);
    return card;
  }

  /** Answer times under a second read as "0s", which looks like missing data. */
  function formatThinkingTime(seconds) {
    const value = Number(seconds) || 0;
    if (value < 1) return "< 1s";
    if (value < 60) return `${Math.round(value)}s`;
    const mins = Math.floor(value / 60);
    return `${mins}m ${Math.round(value % 60)}s`;
  }

  function interaction(qa) {
    const block = el("div", {
      class: `qa-block ${qa.correct ? "correct" : "incorrect"}`,
      style: "margin-top:var(--sp-3)",
    });
    block.innerHTML = `
      <div class="qa-label">Question asked</div>
      <div style="margin-bottom:var(--sp-2)">${escapeHtml(qa.question_text)}</div>
      <div class="qa-label">Your answer${
        qa.response_time_sec ? ` · ${formatThinkingTime(qa.response_time_sec)}` : ""
      }</div>
      <div style="margin-bottom:var(--sp-2)">${escapeHtml(qa.raw_answer || "No answer recorded")}</div>
      <div class="qa-label">Graded ${
        qa.correct ? "correct" : `${Math.round((qa.partial_credit || 0) * 100)}% credit`
      }</div>
      <div style="color:var(--text-muted)">${escapeHtml(qa.feedback_text || "")}</div>
      ${
        qa.misconception_tag
          ? `<div style="margin-top:8px"><span class="chip chip-weak">${escapeHtml(
              qa.misconception_tag
            )}</span></div>`
          : ""
      }
      ${
        qa.adaptation_action && qa.adaptation_action !== "ALLOW"
          ? `<div class="subtle" style="margin-top:8px">→ ${escapeHtml(qa.adaptation_reason || "")}</div>`
          : ""
      }`;
    return block;
  }
}
