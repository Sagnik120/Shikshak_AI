/** Lesson history: search, filter, paginate, resume or delete. */
import { api } from "../api.js";
import {
  $, el, clear, escapeHtml, icon, toast, requireAuth, mountHeader,
  formatRelative, formatDuration, confirmDialog, emptyState,
  STATUS_META, LEVEL_LABELS, LANGUAGE_LABELS, scoreClass,
} from "../ui.js";

const user = await requireAuth();
if (user) {
  mountHeader(user, "/lessons.html");

  const PAGE_SIZE = 20;
  const state = { search: "", status: "all", offset: 0, lessons: [], total: 0 };

  const card = $("#lessons-card");
  const loadMore = $("#load-more");

  // Debounce so typing doesn't fire a request per keystroke.
  let debounce;
  $("#search").addEventListener("input", (event) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      state.search = event.target.value.trim();
      reload();
    }, 300);
  });

  $("#status-filter").addEventListener("change", (event) => {
    state.status = event.target.value;
    reload();
  });

  loadMore.addEventListener("click", () => load(false));

  async function reload() {
    state.offset = 0;
    state.lessons = [];
    await load(true);
  }

  async function load(replace) {
    if (replace) {
      clear(card).append(
        el("div", { class: "card-body" }, el("div", { class: "skeleton", style: "height:64px" }))
      );
    }

    try {
      const data = await api.listLessons({
        search: state.search,
        status: state.status,
        limit: PAGE_SIZE,
        offset: state.offset,
      });

      state.lessons = replace ? data.lessons : [...state.lessons, ...data.lessons];
      state.total = data.total;
      state.offset += data.lessons.length;

      render();
      loadMore.hidden = !data.has_more;
    } catch (error) {
      clear(card).append(
        emptyState("alert", "Couldn't load your lessons", error.message,
          el("button", { class: "btn btn-primary", onclick: reload }, "Try again"))
      );
    }
  }

  function render() {
    clear(card);

    if (!state.lessons.length) {
      const filtering = state.search || state.status !== "all";
      card.append(
        filtering
          ? emptyState("book", "No lessons match", "Try a different search term or status filter.")
          : emptyState(
              "book",
              "No lessons yet",
              "Build your first lesson from a chapter you're revising or a topic you're stuck on.",
              el("a", { class: "btn btn-primary", href: "/new-lesson.html" }, "Create a lesson")
            )
      );
      return;
    }

    const head = el("div", { class: "card-header" });
    head.innerHTML = `<h2 class="card-title">${state.total} lesson${
      state.total === 1 ? "" : "s"
    }</h2><span class="subtle">Showing ${state.lessons.length}</span>`;
    card.append(head);

    const list = el("div");
    state.lessons.forEach((lesson) => list.append(row(lesson)));
    card.append(list);
  }

  function row(lesson) {
    const status = STATUS_META[lesson.status] || STATUS_META.created;
    const href =
      lesson.status === "completed"
        ? `/report.html?lesson=${encodeURIComponent(lesson.id)}`
        : `/classroom.html?lesson=${encodeURIComponent(lesson.id)}`;

    const node = el("div", { class: "lesson-row" });
    node.innerHTML = `
      <div class="lesson-row-main">
        <a href="${href}" class="lesson-row-title" style="color:inherit">${escapeHtml(lesson.title)}</a>
        <div class="lesson-row-meta">
          <span class="${status.cls}">${status.label}</span>
          <span>${lesson.nodes_completed}/${lesson.node_count} concepts</span>
          <span>${escapeHtml(LEVEL_LABELS[lesson.level] || lesson.level)}</span>
          <span>${escapeHtml(LANGUAGE_LABELS[lesson.language] || lesson.language)}</span>
          <span>${escapeHtml(formatDuration(lesson.watch_minutes))} watched</span>
          <span>${escapeHtml(formatRelative(lesson.updated_at))}</span>
        </div>
        ${
          lesson.status === "in_progress"
            ? `<div class="progress-track" style="margin-top:8px;max-width:260px">
                 <div class="progress-fill" style="width:${lesson.progress_pct}%"></div>
               </div>`
            : ""
        }
      </div>
      <div class="row" style="gap:var(--sp-3)">
        ${
          lesson.score_pct !== null && lesson.score_pct !== undefined
            ? `<span class="lesson-row-score" style="color:var(--${
                scoreClass(lesson.score_pct) === "high"
                  ? "green-600"
                  : scoreClass(lesson.score_pct) === "mid"
                  ? "amber-600"
                  : "rose-600"
              })">${lesson.score_pct}%</span>`
            : ""
        }
        <a class="btn btn-secondary btn-sm" href="${href}">${
          lesson.status === "completed" ? "Report" : lesson.status === "in_progress" ? "Resume" : "Start"
        }</a>
        <button class="btn btn-ghost btn-icon" data-delete title="Delete lesson"
                aria-label="Delete ${escapeHtml(lesson.title)}">${icon("trash", 16)}</button>
      </div>`;

    $("[data-delete]", node).addEventListener("click", async () => {
      const ok = await confirmDialog({
        title: "Delete this lesson?",
        body: `"${lesson.title}" and all its recorded answers and videos will be permanently removed.`,
        confirmLabel: "Delete lesson",
        danger: true,
      });
      if (!ok) return;
      try {
        await api.deleteLesson(lesson.id);
        toast("Lesson deleted.");
        reload();
      } catch (error) {
        toast(error.message, "error");
      }
    });

    return node;
  }

  await load(true);
}
