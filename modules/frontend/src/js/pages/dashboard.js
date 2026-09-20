/** Dashboard: live stats, resume banner, recent lessons, mastery, activity. */
import { api } from "../api.js";
import {
  $, el, clear, escapeHtml, icon, toast, requireAuth, mountHeader,
  formatRelative, formatDuration, plural, STATUS_META, LEVEL_LABELS, emptyState,
} from "../ui.js";

const user = await requireAuth();
if (user) {
  mountHeader(user, "/dashboard.html");

  if (new URLSearchParams(window.location.search).get("welcome") === "1") {
    toast(`Welcome to Shikshak, ${user.full_name.split(" ")[0]}. Your account is verified.`, "success", 6000);
    window.history.replaceState({}, "", "/dashboard.html");
  }

  const root = $("#dash-root");

  try {
    render(await api.dashboard());
  } catch (error) {
    clear(root).append(
      emptyState(
        "alert",
        "Couldn't load your dashboard",
        error.message,
        el("button", { class: "btn btn-primary", onclick: () => window.location.reload() }, "Try again")
      )
    );
  }

  function render(data) {
    const { stats, learner } = data;
    const firstName = escapeHtml(learner.full_name.split(" ")[0]);

    clear(root);
    root.append(
      buildHeading(firstName, stats),
      buildStats(stats),
      ...(data.resume_lesson ? [buildResume(data.resume_lesson)] : []),
      buildMainGrid(data)
    );
  }

  function buildHeading(firstName, stats) {
    const node = el("div", { class: "row-between row-wrap", style: "margin-bottom:var(--sp-6)" });
    node.innerHTML = `
      <div>
        <h1>${greeting()}, ${firstName}.</h1>
        <p class="muted" style="margin-top:4px">${summaryLine(stats)}</p>
      </div>
      <a class="btn btn-primary" href="/new-lesson.html">${icon("plus", 18)} Start a new lesson</a>`;
    return node;
  }

  function greeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  }

  function summaryLine(stats) {
    if (!stats.lessons_started) return "You haven't started a lesson yet — pick a topic and Shikshak will build one.";
    if (stats.lessons_in_progress) {
      return `${stats.lessons_in_progress} lesson${stats.lessons_in_progress > 1 ? "s" : ""} in progress · ${
        stats.concepts_mastered
      } concept${stats.concepts_mastered === 1 ? "" : "s"} mastered so far.`;
    }
    return `${stats.lessons_completed} lesson${stats.lessons_completed === 1 ? "" : "s"} completed · ${
      stats.accuracy_pct
    }% of checkpoint questions answered correctly.`;
  }

  function buildStats(stats) {
    const cards = [
      { label: "Lessons completed", value: stats.lessons_completed, meta: `${stats.lessons_started} started` },
      { label: "Average score", value: `${stats.average_score_pct}%`, meta: `${stats.total_questions} questions answered` },
      { label: "Concepts mastered", value: stats.concepts_mastered, meta: `${stats.concepts_to_review} to review` },
      {
        label: "Day streak",
        value: stats.streak_days,
        meta: stats.longest_streak
          ? `Best: ${stats.longest_streak} day${stats.longest_streak === 1 ? "" : "s"}`
          : "Start one today",
      },
    ];

    const grid = el("div", { class: "stat-grid", style: "margin-bottom:var(--sp-5)" });
    grid.innerHTML = cards
      .map(
        (c) => `<div class="stat">
          <div class="stat-label">${escapeHtml(c.label)}</div>
          <div class="stat-value">${escapeHtml(String(c.value))}</div>
          <div class="stat-meta">${escapeHtml(c.meta)}</div>
        </div>`
      )
      .join("");
    return grid;
  }

  function buildResume(lesson) {
    const node = el("div", { class: "resume-card", style: "margin-bottom:var(--sp-5)" });
    node.innerHTML = `
      <div class="row-between row-wrap" style="align-items:flex-start;gap:var(--sp-4)">
        <div class="grow">
          <span class="badge" style="background:rgba(255,255,255,.18);color:#fff">Pick up where you left off</span>
          <h2 style="margin-top:var(--sp-3)">${escapeHtml(lesson.title)}</h2>
          <p style="color:rgba(255,255,255,.78);font-size:var(--text-sm);margin-top:6px">
            ${lesson.nodes_completed} of ${lesson.node_count} concepts done · last active ${escapeHtml(
              formatRelative(lesson.updated_at)
            )}
          </p>
          <div class="progress-track" style="margin-top:var(--sp-4);max-width:420px">
            <div class="progress-fill" style="width:${lesson.progress_pct}%"></div>
          </div>
        </div>
        <a class="btn btn-lg" href="/classroom.html?lesson=${encodeURIComponent(lesson.id)}"
           style="background:#fff;color:var(--indigo-700)">Resume lesson</a>
      </div>`;
    return node;
  }

  function buildMainGrid(data) {
    const grid = el("div", { class: "dash-grid" });
    grid.append(buildRecentLessons(data.recent_lessons), buildSidebar(data));
    return grid;
  }

  function buildRecentLessons(lessons) {
    const card = el("section", { class: "card" });
    const head = el("div", { class: "card-header" });
    head.innerHTML = `<h2 class="card-title">Recent lessons</h2>
      <a href="/lessons.html" style="font-size:var(--text-sm);font-weight:600">View all</a>`;
    card.append(head);

    if (!lessons.length) {
      card.append(
        emptyState(
          "book",
          "No lessons yet",
          "Upload a chapter or type a topic, and Shikshak will plan and teach it.",
          el("a", { class: "btn btn-primary", href: "/new-lesson.html" }, "Create your first lesson")
        )
      );
      return card;
    }

    const list = el("div");
    for (const lesson of lessons) {
      const status = STATUS_META[lesson.status] || STATUS_META.created;
      const href =
        lesson.status === "completed"
          ? `/report.html?lesson=${encodeURIComponent(lesson.id)}`
          : `/classroom.html?lesson=${encodeURIComponent(lesson.id)}`;

      const row = el("a", { class: "lesson-row", href, style: "text-decoration:none;color:inherit" });
      row.innerHTML = `
        <div class="lesson-row-main">
          <div class="lesson-row-title">${escapeHtml(lesson.title)}</div>
          <div class="lesson-row-meta">
            <span class="${status.cls}">${status.label}</span>
            <span>${lesson.nodes_completed}/${lesson.node_count} concepts</span>
            <span>${escapeHtml(LEVEL_LABELS[lesson.level] || lesson.level)}</span>
            <span>${escapeHtml(formatRelative(lesson.updated_at))}</span>
          </div>
        </div>
        ${
          lesson.score_pct !== null && lesson.score_pct !== undefined
            ? `<div class="lesson-row-score" style="color:var(--${
                lesson.score_pct >= 75 ? "green-600" : lesson.score_pct >= 50 ? "amber-600" : "rose-600"
              })">${lesson.score_pct}%</div>`
            : `<span class="subtle">${lesson.progress_pct}%</span>`
        }`;
      list.append(row);
    }
    card.append(list);
    return card;
  }

  function buildSidebar(data) {
    const column = el("div", { class: "stack", style: "--gap:var(--sp-5)" });

    // Learning time
    const time = el("section", { class: "card card-pad" });
    time.innerHTML = `
      <div class="section-label">Time invested</div>
      <div class="stat-value" style="font-size:var(--text-2xl)">${escapeHtml(
        formatDuration(data.stats.learning_minutes)
      )}</div>
      <div class="stat-meta">${data.stats.correct_questions} of ${data.stats.total_questions} checkpoint answers correct</div>`;
    column.append(time);

    // Mastery chips
    const mastery = el("section", { class: "card" });
    mastery.innerHTML = `<div class="card-header"><h2 class="card-title">Concept mastery</h2></div>`;
    const masteryBody = el("div", { class: "card-body stack", style: "--gap:var(--sp-4)" });

    if (!data.strong_concepts.length && !data.weak_concepts.length) {
      masteryBody.innerHTML = `<p class="subtle">Answer some checkpoint questions and your mastery map will build here.</p>`;
    } else {
      if (data.strong_concepts.length) {
        masteryBody.append(chipGroup("Strong", data.strong_concepts, "chip-strong"));
      }
      if (data.weak_concepts.length) {
        masteryBody.append(chipGroup("Needs review", data.weak_concepts, "chip-weak"));
      }
      if (data.misconceptions.length) {
        const mis = el("div");
        mis.innerHTML = `<div class="section-label" style="margin-bottom:var(--sp-2)">Recurring misconceptions</div>
          <div class="chip-cloud">${data.misconceptions
            .map((m) => `<span class="chip">${escapeHtml(m.tag)} · ${m.count}×</span>`)
            .join("")}</div>`;
        masteryBody.append(mis);
      }
    }
    mastery.append(masteryBody);
    column.append(mastery);

    // Activity heat strip
    const activity = el("section", { class: "card card-pad" });
    const counts = data.activity_calendar.map((d) => d.count);
    const max = Math.max(1, ...counts);
    activity.innerHTML = `
      <div class="row-between" style="margin-bottom:var(--sp-3)">
        <div class="section-label">Last 12 weeks</div>
        <span class="subtle">${plural(counts.reduce((a, b) => a + b, 0), "session")}</span>
      </div>
      <div class="heat-grid">${data.activity_calendar
        .map(
          (day) =>
            `<div class="heat-cell" data-level="${level(day.count, max)}" title="${escapeHtml(
              day.date
            )}: ${day.count} lesson${day.count === 1 ? "" : "s"}"></div>`
        )
        .join("")}</div>`;
    column.append(activity);

    return column;
  }

  function chipGroup(label, items, cls) {
    const node = el("div");
    node.innerHTML = `<div class="section-label" style="margin-bottom:var(--sp-2)">${escapeHtml(label)}</div>
      <div class="chip-cloud">${items
        .map((c) => `<span class="chip ${cls}">${escapeHtml(c)}</span>`)
        .join("")}</div>`;
    return node;
  }

  function level(count, max) {
    if (!count) return 0;
    return Math.min(4, Math.ceil((count / max) * 4));
  }
}
