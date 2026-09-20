/** Lesson builder: upload or pick a source, tune constraints, generate a plan. */
import { api } from "../api.js";
import {
  $, $$, el, clear, escapeHtml, icon, toast, requireAuth, mountHeader,
  showAlert, hideAlert, setLoading, confirmDialog, formatRelative,
} from "../ui.js";

const user = await requireAuth();
if (user) {
  mountHeader(user, "/new-lesson.html");

  const state = {
    documentId: null,
    documentName: null,
    topic: "",
    level: user.preferred_level || "beginner",
    language: user.preferred_language || "en",
    budget: String(user.default_time_budget_min || 15),
    lessonId: null,
  };

  const alertBox = $("#page-alert");
  const buildBtn = $("#build-btn");
  const readyNote = $("#ready-note");
  const topicInput = $("#topic");
  const planCard = $("#plan-card");

  // --- seed the controls from the learner's saved preferences ---
  $("#language").value = state.language;
  $("#budget").value = state.budget;
  $$("#level-group button").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.value === state.level))
  );
  $("#defaults-note").textContent = "Pre-filled from your account preferences";

  // --- tuning controls ---
  $("#level-group").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-value]");
    if (!button) return;
    state.level = button.dataset.value;
    $$("#level-group button").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
  });
  $("#language").addEventListener("change", (e) => (state.language = e.target.value));
  $("#budget").addEventListener("change", (e) => (state.budget = e.target.value));

  // --- topic ---
  topicInput.addEventListener("input", () => {
    state.topic = topicInput.value.trim();
    // A typed topic and a selected document are mutually exclusive sources.
    if (state.topic && state.documentId) selectDocument(null);
    refreshReadiness();
  });

  $("#suggestions").addEventListener("click", (event) => {
    const chip = event.target.closest(".suggestion");
    if (!chip) return;
    topicInput.value = chip.textContent.trim();
    topicInput.dispatchEvent(new Event("input"));
    topicInput.focus();
  });

  // --- upload ---
  const dropzone = $("#dropzone");
  const fileInput = $("#file-input");

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });
  ["dragenter", "dragover"].forEach((name) =>
    dropzone.addEventListener(name, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((name) =>
    dropzone.addEventListener(name, (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragover");
    })
  );
  dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (file) upload(file);
  });
  fileInput.addEventListener("change", () => {
    const file = fileInput.files?.[0];
    if (file) upload(file);
    fileInput.value = "";
  });

  const MAX_BYTES = 25 * 1024 * 1024;
  const ALLOWED = [".pdf", ".docx", ".pptx", ".txt", ".md"];

  async function upload(file) {
    hideAlert(alertBox);

    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED.includes(ext)) {
      showAlert(alertBox, `Shikshak can't read ${ext} files. Use ${ALLOWED.join(", ")}.`, "error");
      return;
    }
    if (file.size > MAX_BYTES) {
      showAlert(alertBox, "That file is larger than 25 MB.", "error");
      return;
    }

    const wrap = $("#upload-progress");
    const bar = $("#upload-bar");
    const pct = $("#upload-pct");
    const label = $("#upload-label");

    wrap.hidden = false;
    label.textContent = `Uploading ${file.name}…`;
    bar.style.width = "0%";
    pct.textContent = "0%";

    try {
      const document_ = await api.uploadDocument(file, (percent) => {
        bar.style.width = `${percent}%`;
        pct.textContent = `${percent}%`;
        // The server still has to parse, chunk, and index after the bytes land.
        if (percent >= 100) label.textContent = "Reading and indexing the document…";
      });

      wrap.hidden = true;
      toast(`${document_.filename} is ready — ${document_.chunk_count} sections indexed.`, "success");
      await loadDocuments();
      selectDocument(document_.document_id, document_.filename);
    } catch (error) {
      wrap.hidden = true;
      showAlert(alertBox, error.message, "error");
    }
  }

  async function loadDocuments() {
    const list = $("#doc-list");
    let documents = [];
    try {
      documents = await api.listDocuments();
    } catch {
      return;
    }

    clear(list);
    if (!documents.length) return;

    list.append(
      el("div", { class: "section-label", style: "margin-bottom:var(--sp-2)" }, "Your uploaded material")
    );

    for (const doc of documents) {
      const item = el("div", {
        class: "doc-item",
        role: "button",
        tabindex: "0",
        "aria-pressed": String(doc.document_id === state.documentId),
        style: "margin-bottom:var(--sp-2)",
      });
      item.innerHTML = `
        <span class="doc-icon">${icon("file", 18)}</span>
        <span class="grow">
          <span class="doc-name">${escapeHtml(doc.filename)}</span>
          <span class="subtle" style="display:block;font-size:11px">
            ${doc.chunk_count} sections · ${escapeHtml(formatRelative(doc.created_at))}
            ${doc.status !== "ready" ? ` · ${escapeHtml(doc.status)}` : ""}
          </span>
        </span>
        <button class="btn btn-ghost btn-icon" data-delete="${escapeHtml(doc.document_id)}"
                title="Delete this document" aria-label="Delete ${escapeHtml(doc.filename)}">${icon("trash", 16)}</button>`;

      item.addEventListener("click", (event) => {
        if (event.target.closest("[data-delete]")) return;
        if (doc.status !== "ready") {
          toast("That document isn't ready yet.", "error");
          return;
        }
        selectDocument(doc.document_id === state.documentId ? null : doc.document_id, doc.filename);
      });
      item.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          item.click();
        }
      });

      $("[data-delete]", item).addEventListener("click", async (event) => {
        event.stopPropagation();
        const ok = await confirmDialog({
          title: "Delete this document?",
          body: `${doc.filename} will be removed. Lessons already built from it keep their content.`,
          confirmLabel: "Delete",
          danger: true,
        });
        if (!ok) return;
        try {
          await api.deleteDocument(doc.document_id);
          if (state.documentId === doc.document_id) selectDocument(null);
          toast("Document deleted.");
          loadDocuments();
        } catch (error) {
          toast(error.message, "error");
        }
      });

      list.append(item);
    }
  }

  function selectDocument(id, name) {
    state.documentId = id;
    state.documentName = id ? name : null;
    if (id) {
      topicInput.value = "";
      state.topic = "";
    }
    $$("#doc-list .doc-item").forEach((item) => {
      const itemId = $("[data-delete]", item)?.dataset.delete;
      item.setAttribute("aria-pressed", String(itemId === id));
    });
    refreshReadiness();
  }

  function refreshReadiness() {
    const ready = Boolean(state.documentId || state.topic);
    buildBtn.disabled = !ready;

    if (state.documentId) {
      readyNote.textContent = `Shikshak will teach from ${state.documentName}, staying grounded in that material.`;
    } else if (state.topic) {
      readyNote.textContent = `Shikshak will build a lesson on "${state.topic.slice(0, 80)}${
        state.topic.length > 80 ? "…" : ""
      }".`;
    } else {
      readyNote.textContent = "Choose a source above to continue.";
    }
  }

  // --- build ---
  buildBtn.addEventListener("click", async () => {
    hideAlert(alertBox);
    setLoading(buildBtn, true);
    readyNote.textContent = "Planning your lesson — this takes a few seconds…";

    try {
      const lesson = await api.createLesson({
        topic: state.topic || null,
        document_id: state.documentId,
        level: state.level,
        language: state.language,
        time_budget_min: Number(state.budget),
      });
      state.lessonId = lesson.lesson_id;

      const result = await api.generatePlan(state.lessonId);
      renderPlan(result.plan);
    } catch (error) {
      showAlert(alertBox, error.message, "error");
      readyNote.textContent = "";
      refreshReadiness();
      // The empty lesson row would otherwise clutter the learner's history.
      if (state.lessonId) {
        try {
          await api.deleteLesson(state.lessonId);
        } catch {
          /* best effort */
        }
        state.lessonId = null;
      }
    } finally {
      setLoading(buildBtn, false, "Build my lesson");
    }
  });

  function renderPlan(plan) {
    const nodes = plan?.nodes || [];
    $("#plan-count").textContent = `${nodes.length} concept${nodes.length === 1 ? "" : "s"}`;

    const host = clear($("#plan-nodes"));
    const totalMinutes = nodes.reduce((sum, n) => sum + (n.est_minutes || 0), 0);

    for (const [index, node] of nodes.entries()) {
      const row = el("div", { class: "plan-node" });
      row.innerHTML = `
        <span class="plan-index">${index + 1}</span>
        <span class="grow">
          <span style="font-weight:600;display:block">${escapeHtml(node.concept)}</span>
          <span class="lesson-row-meta">
            <span class="badge">${escapeHtml(node.depth)}</span>
            <span>${node.est_minutes} min</span>
            <span>${escapeHtml(node.visual_type)} board</span>
            ${node.checkpoint_question ? '<span class="badge badge-accent">Checkpoint</span>' : ""}
          </span>
        </span>`;
      host.append(row);
    }

    host.append(
      el(
        "p",
        { class: "subtle", style: "margin-top:var(--sp-4)" },
        `About ${totalMinutes} minutes of teaching, with ${
          nodes.filter((n) => n.checkpoint_question).length
        } checkpoint questions along the way.`
      )
    );

    planCard.hidden = false;
    planCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    readyNote.textContent = "Your plan is ready.";
  }

  $("#start-btn").addEventListener("click", () => {
    window.location.href = `/classroom.html?lesson=${encodeURIComponent(state.lessonId)}`;
  });

  $("#discard-btn").addEventListener("click", async () => {
    const ok = await confirmDialog({
      title: "Discard this plan?",
      body: "The lesson will be deleted and you can build a new one.",
      confirmLabel: "Discard",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteLesson(state.lessonId);
    } catch {
      /* already gone is fine */
    }
    state.lessonId = null;
    planCard.hidden = true;
    refreshReadiness();
  });

  await loadDocuments();
  refreshReadiness();
}
