/**
 * Live classroom: drives the teaching WebSocket, plays each rendered segment,
 * collects checkpoint answers, and reflects graded progress as it happens.
 */
import { api, openLessonSocket, tokens } from "../api.js";
import {
  $, el, clear, escapeHtml, icon, toast, requireAuth, formatSeconds,
} from "../ui.js";

const user = await requireAuth();
const lessonId = new URLSearchParams(window.location.search).get("lesson");

if (user && !lessonId) {
  window.location.replace("/new-lesson.html");
} else if (user) {
  const dom = {
    title: $("#lesson-title"),
    connection: $("#connection-badge"),
    statusText: $("#status-text"),
    overlay: $("#overlay"),
    overlayTitle: $("#overlay-title"),
    overlayBody: $("#overlay-body"),
    overlayActions: $("#overlay-actions"),
    practiceLink: $("#practice-link"),
    rewatch: $("#rewatch"),
    rewatchTitle: $("#rewatch-title"),
    rewatchVideo: $("#rewatch-video"),
    rewatchClose: $("#rewatch-close"),
    video: $("#video"),
    nodeList: $("#node-list"),
    progressBar: $("#progress-bar"),
    progressLabel: $("#progress-label"),
    checkpoint: $("#checkpoint"),
    checkpointKind: $("#checkpoint-kind"),
    questionText: $("#question-text"),
    options: $("#options"),
    freeAnswer: $("#free-answer"),
    answerInput: $("#answer-input"),
    submitAnswer: $("#submit-answer"),
    answerHint: $("#answer-hint"),
    feedback: $("#feedback"),
    citation: $("#citation"),
    citationText: $("#citation-text"),
    notes: $("#chapter-notes"),
    notesConcept: $("#notes-concept"),
    notesDepth: $("#notes-depth"),
    notesMinutes: $("#notes-minutes"),
    notesFormula: $("#notes-formula"),
    notesPoints: $("#notes-points"),
    notesExampleWrap: $("#notes-example-wrap"),
    notesExample: $("#notes-example"),
    notesTranscript: $("#notes-transcript"),
    adaptationBanner: $("#adaptation-banner"),
    adaptationSpinner: $("#adaptation-spinner"),
    adaptationIcon: $("#adaptation-icon"),
    adaptationText: $("#adaptation-text"),
    lessonNotes: $("#lesson-notes"),
    lessonNotesList: $("#lesson-notes-list"),
    downloadNotes: $("#download-notes"),
    log: $("#event-log"),
  };

  const state = {
    socket: null,
    nodes: [],
    currentNodeId: null,
    question: null,
    selectedOption: null,
    questionShownAt: 0,
    objectUrls: [],
    closedByUs: false,
    // One entry per concept taught, in order, for the class notes panel.
    collectedNotes: [],
    // Dedupe key for the adaptation banner so a reconnect/resend can't stack it.
    lastAdaptationKey: null,
    // The segment currently loaded in the player, so a reconnect that replays
    // it doesn't restart the video from 0:00.
    playing: null,
    // An answer is being graded: Submit stays disabled.
    grading: false,
    // The lesson was handed to a human: the video must not play.
    lessonStopped: false,
    reconnectAttempts: 0,
    reconnectTimer: null,
  };

  const MAX_RECONNECT_ATTEMPTS = 8;

  const QUESTION_KIND = {
    mcq: "Multiple choice",
    short_answer: "Short answer",
    problem: "Problem",
    application: "Apply it",
    explain_in_own_words: "In your own words",
  };

  /* ---------------------------------------------------------------------
     Presentation helpers
     --------------------------------------------------------------------- */

  function log(message) {
    const time = new Date().toLocaleTimeString([], { hour12: false });
    const line = el("div");
    line.innerHTML = `<span class="t">${time}</span> ${escapeHtml(message)}`;
    dom.log.append(line);
    dom.log.scrollTop = dom.log.scrollHeight;
  }

  function setConnection(label, variant = "") {
    dom.connection.className = `badge ${variant}`;
    dom.connection.innerHTML = `<span class="dot${
      variant === "badge-green" ? "" : " dot-pulse"
    }"></span> ${escapeHtml(label)}`;
  }

  function setStatus(text) {
    dom.statusText.textContent = text;
  }

  function showOverlay(title, body) {
    dom.overlayTitle.textContent = title;
    dom.overlayBody.textContent = body;
    clear(dom.overlayActions);
    dom.overlayActions.hidden = true;
    dom.overlay.hidden = false;
    // The overlay covers the player; a hidden video must not keep talking.
    dom.video.pause();
  }

  function hideOverlay() {
    dom.overlay.hidden = true;
  }

  /* ---------------------------------------------------------------------
     Rewatch an earlier concept: the live lesson pauses where it is and
     continues untouched afterwards. No server calls besides the video.
     --------------------------------------------------------------------- */

  const rewatch = { open: false, url: null, resumeLive: false };

  async function openRewatch(node) {
    if (rewatch.open) return;
    rewatch.open = true;
    rewatch.resumeLive = !dom.video.paused;
    dom.video.pause();
    dom.rewatchTitle.textContent = `Rewatching: ${node.concept}`;
    dom.rewatch.hidden = false;
    try {
      rewatch.url = await api.mediaObjectUrl(node.video_url);
      if (!rewatch.open) return URL.revokeObjectURL(rewatch.url);
      dom.rewatchVideo.src = rewatch.url;
      dom.rewatchVideo.play().catch(() => {});
    } catch (error) {
      toast(`Couldn't load that video: ${error.message}`, "error");
      closeRewatch();
    }
  }

  function closeRewatch() {
    if (!rewatch.open) return;
    rewatch.open = false;
    dom.rewatchVideo.pause();
    dom.rewatchVideo.removeAttribute("src");
    dom.rewatchVideo.load();
    if (rewatch.url) URL.revokeObjectURL(rewatch.url);
    rewatch.url = null;
    dom.rewatch.hidden = true;
    // Carry on exactly where the lesson was, unless it's waiting on a question.
    if (rewatch.resumeLive && !state.lessonStopped && state.playing?.awaiting == null && !dom.video.hidden) {
      dom.video.play().catch(() => {});
    }
  }

  dom.rewatchClose.addEventListener("click", closeRewatch);
  dom.rewatch.addEventListener("click", (event) => { if (event.target === dom.rewatch) closeRewatch(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeRewatch(); });
  dom.practiceLink.href = `/review.html?lesson=${encodeURIComponent(lessonId)}#practice`;

  /** The end of the lesson with concepts still to review: not completed. */
  function showReviewNeeded(concepts) {
    state.closedByUs = true;
    state.lessonStopped = true;
    dom.video.pause();
    dom.checkpoint.hidden = true;
    setStatus("Almost done");
    setConnection("Paused", "badge-amber");
    const n = concepts.length;
    showOverlay(
      `Almost done — ${n} concept${n === 1 ? "" : "s"} to review`,
      `You skipped or didn't master: ${concepts.map((c) => c.concept).join(", ")}. ` +
        "Review them to complete this lesson and get your report."
    );
    const next = concepts[0];
    const go = el("button", { class: "btn btn-primary btn-sm", type: "button" }, `Review next: ${next.concept}`);
    go.addEventListener("click", async () => {
      go.disabled = true;
      go.textContent = "One moment…";
      try {
        await api.relearnConcept(lessonId, next.node_id);
        window.location.reload();
      } catch (error) {
        toast(error.message, "error", 6000);
        go.disabled = false;
        go.textContent = `Review next: ${next.concept}`;
      }
    });
    const practise = el("a", { class: "btn btn-secondary btn-sm", href: `/review.html?lesson=${encodeURIComponent(lessonId)}` },
      "Review & practise");
    dom.overlayActions.append(go, practise);
    dom.overlayActions.hidden = false;
  }

  /** Paused for a mentor: never teach on silently — offer the ways forward. */
  function showPaused(escalation) {
    state.closedByUs = true;
    state.lessonStopped = true;
    dom.video.pause();
    dom.video.controls = false;
    dom.checkpoint.hidden = true;
    setStatus("Paused");
    setConnection("Paused", "badge-rose");
    const concept = escalation?.concept ? `“${escalation.concept}”` : "this concept";
    showOverlay(
      "Waiting for your mentor",
      `This lesson is paused at ${concept}. Your mentor has been told. You can review and practise, or choose how to go on.`
    );
    const review = el("a", { class: "btn btn-secondary btn-sm", href: `/review.html?lesson=${encodeURIComponent(lessonId)}` },
      "Review & practise");
    const again = el("button", { class: "btn btn-primary btn-sm", type: "button" }, "Continue — teach it again");
    const skip = el("button", { class: "btn btn-secondary btn-sm", type: "button" }, "Skip this concept");
    const act = async (button, call) => {
      [again, skip].forEach((b) => (b.disabled = true));
      button.textContent = "One moment…";
      try {
        await call();
        window.location.reload(); // start the lesson fresh from the chosen point
      } catch (error) {
        toast(error.message, "error", 6000);
        [again, skip].forEach((b) => (b.disabled = false));
      }
    };
    again.addEventListener("click", () => act(again, () => api.continueLesson(lessonId)));
    skip.addEventListener("click", () => act(skip, () => api.skipConcept(lessonId)));
    dom.overlayActions.append(review, again, skip);
    dom.overlayActions.hidden = false;
  }

  /* ---------------------------------------------------------------------
     Curriculum rail
     --------------------------------------------------------------------- */

  function renderNodes() {
    clear(dom.nodeList);

    state.nodes.forEach((node, index) => {
      const item = el("div", {
        class: `node-item${node.node_id === state.currentNodeId ? " active" : ""}`,
        "data-status": node.status || "pending",
        "data-node": node.node_id,
      });

      const mastered = node.status === "mastered" || node.status === "completed";
      // Finished concepts can be rewatched right here, without leaving the lesson.
      const canRewatch = Boolean(node.video_url) && node.node_id !== state.currentNodeId
        && ["mastered", "completed", "skipped"].includes(node.status);
      if (canRewatch) {
        item.dataset.rewatch = "";
        item.title = "Rewatch this concept";
        item.addEventListener("click", () => openRewatch(node));
      }
      item.innerHTML = `
        <span class="node-marker">${mastered ? icon("check", 13) : index + 1}</span>
        <span class="grow">
          <span class="node-concept">${escapeHtml(node.concept)}</span>
          <span class="node-meta">${statusLabel(node)}</span>
        </span>`;
      dom.nodeList.append(item);
    });

    const active = $(".node-item.active", dom.nodeList);
    active?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  }

  function statusLabel(node) {
    switch (node.status) {
      case "mastered":
        return `Mastered${node.attempts > 1 ? ` · ${node.attempts} attempts` : ""}`;
      case "struggling":
        return `Revisiting · ${node.attempts} attempt${node.attempts === 1 ? "" : "s"}`;
      case "teaching":
        return "Being taught now";
      case "questioning":
        return "Question in progress";
      case "completed":
        return "Watched";
      case "skipped":
        return "To review";
      default:
        return node.checkpoint_question ? "Has a checkpoint" : "Up next";
    }
  }

  function applySnapshot(snapshot) {
    state.nodes = snapshot.nodes || [];
    dom.progressBar.style.width = `${snapshot.progress_pct}%`;
    dom.progressLabel.textContent = `${snapshot.nodes_completed} / ${snapshot.node_count}`;
    renderNodes();
  }

  /* ---------------------------------------------------------------------
     Checkpoint question
     --------------------------------------------------------------------- */

  function showQuestion(payload) {
    state.question = payload;
    state.selectedOption = null;
    state.questionShownAt = Date.now();

    dom.feedback.hidden = true;
    dom.submitAnswer.textContent = "Submit answer";
    // Distinguishes a fresh question from a card left over from the last one.
    dom.checkpoint.dataset.interaction = payload.interaction_id || "";
    dom.checkpointKind.textContent = QUESTION_KIND[payload.type] || "Checkpoint";
    dom.questionText.textContent = payload.question_text;

    clear(dom.options);
    const isMcq = Array.isArray(payload.options) && payload.options.length > 0;

    if (isMcq) {
      dom.freeAnswer.hidden = true;
      dom.options.hidden = false;
      payload.options.forEach((option, index) => {
        const button = el("button", {
          class: "option",
          type: "button",
          "aria-pressed": "false",
          "data-value": option,
        });
        button.innerHTML = `<span class="option-radio"></span><span>${escapeHtml(option)}</span>`;
        button.addEventListener("click", () => {
          state.selectedOption = option;
          [...dom.options.children].forEach((child) =>
            child.setAttribute("aria-pressed", String(child === button))
          );
          dom.submitAnswer.disabled = false;
        });
        dom.options.append(button);
      });
      dom.submitAnswer.disabled = true;
      dom.answerHint.textContent = "Pick the option you think is right.";
    } else {
      dom.options.hidden = true;
      dom.freeAnswer.hidden = false;
      dom.answerInput.value = "";
      dom.submitAnswer.disabled = true;
      dom.answerHint.textContent =
        "Answer in your own words — you're graded on understanding, not wording.";
      setTimeout(() => dom.answerInput.focus(), 120);
    }

    dom.checkpoint.hidden = false;
    dom.checkpoint.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  /* ---------------------------------------------------------------------
     Mid-video checkpoints: the video pauses at each one, the learner answers
     a question about what has been covered so far, and it resumes once the
     server allows it. Nothing can be skipped or seeked past.
     --------------------------------------------------------------------- */

  function nextCheckpoint() {
    const seg = state.playing;
    if (!seg?.checkpoints) return null;
    return seg.checkpoints.find((cp) => !seg.passed.has(cp.index)) || null;
  }

  function reachCheckpoint(cp) {
    const seg = state.playing;
    if (!seg || seg.awaiting === cp.index) return;
    seg.awaiting = cp.index;
    dom.video.pause();
    if (Math.abs(dom.video.currentTime - cp.at_sec) > 0.5) dom.video.currentTime = cp.at_sec;
    setStatus("Question time");
    log(`Checkpoint ${cp.index + 1} — pausing for a question`);
    // If the socket is down, the replay after reconnecting sends it again.
    seg.awaitingSent = send("checkpoint_reached", { node_id: seg.node_id, index: cp.index });
  }

  dom.video.addEventListener("timeupdate", () => {
    const cp = nextCheckpoint();
    if (cp && dom.video.currentTime >= cp.at_sec) reachCheckpoint(cp);
  });

  // Paused for a question (or the lesson has stopped): it stays paused.
  dom.video.addEventListener("play", () => {
    if (state.lessonStopped || state.playing?.awaiting != null) dom.video.pause();
  });

  // No seeking past a question that hasn't been answered yet.
  dom.video.addEventListener("seeking", () => {
    const cp = nextCheckpoint();
    if (cp && dom.video.currentTime > cp.at_sec + 0.25) dom.video.currentTime = cp.at_sec;
  });

  function resumeAfterCheckpoint(index) {
    const seg = state.playing;
    if (!seg) return;
    seg.passed.add(index);
    if (seg.awaiting !== index) return;
    seg.awaiting = null;
    // Long enough to read the feedback, then carry on.
    setTimeout(() => {
      if (state.playing !== seg || seg.awaiting != null || state.lessonStopped) return;
      if (rewatch.open) {
        dismissCheckpoint();
        rewatch.resumeLive = true;
        return;
      }
      dismissCheckpoint();
      const atEnd = dom.video.ended || dom.video.currentTime >= (dom.video.duration || Infinity) - 0.3;
      if (atEnd || !seg.video_url) {
        markWatched();
        return;
      }
      setStatus("Teaching");
      dom.video.play().catch(() => toast("Tap play to continue the lesson.", "info", 4000));
    }, 1800);
  }

  /** Tell the server this concept's video is finished, once per segment. */
  function markWatched() {
    const seg = state.playing;
    if (!seg) return;
    seg.done = true; // the learner is finished, even if the socket is down
    if (!seg.sent) seg.sent = send("segment_watched", { node_id: seg.node_id });
  }

  dom.video.addEventListener("ended", () => {
    const cp = nextCheckpoint();
    if (cp) {
      reachCheckpoint(cp); // a checkpoint right at the end
      return;
    }
    markWatched();
  });

  dom.answerInput.addEventListener("input", () => {
    if (state.grading) return; // typing must not re-enable Submit mid-grading
    dom.submitAnswer.disabled = dom.answerInput.value.trim().length < 2;
  });

  // Ctrl/Cmd+Enter submits a written answer without reaching for the mouse.
  dom.answerInput.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && !dom.submitAnswer.disabled) {
      submitAnswer();
    }
  });

  dom.submitAnswer.addEventListener("click", submitAnswer);

  function submitAnswer() {
    if (!state.question) return;

    const answer = state.selectedOption ?? dom.answerInput.value.trim();
    if (!answer) return;

    if (state.grading) return; // one answer per question — no double submits
    const sent = send("student_response", {
      node_id: state.question.node_id,
      // Binds the answer to THIS question, so it can never answer another.
      interaction_id: state.question.interaction_id,
      raw_answer: answer,
      response_time_sec: (Date.now() - state.questionShownAt) / 1000,
    });
    if (!sent) {
      // Keep the answer on screen; it can be submitted once we're reconnected.
      toast("Reconnecting to your classroom — submit again in a moment. Your answer is kept.", "warning", 5000);
      return;
    }

    state.grading = true;
    dom.submitAnswer.disabled = true;
    dom.submitAnswer.textContent = "Grading…";
    dom.answerHint.textContent = "Shikshak is checking your understanding.";
    log(`Answer submitted: ${answer.slice(0, 60)}`);
  }

  /** Make the current question answerable again, keeping what was typed. */
  function resetSubmit() {
    state.grading = false;
    dom.submitAnswer.textContent = "Submit answer";
    dom.submitAnswer.disabled = state.selectedOption == null && dom.answerInput.value.trim().length < 2;
  }

  function showFeedback(evaluation) {
    const credit = evaluation.partial_credit ?? 0;
    const tone = evaluation.correct ? "correct" : credit >= 0.5 ? "partial" : "incorrect";
    const heading = evaluation.correct
      ? "Correct"
      : credit >= 0.5
      ? "Nearly there"
      : "Not quite";

    dom.feedback.className = `feedback ${tone}`;
    dom.feedback.innerHTML = `
      <div class="feedback-title">${icon(evaluation.correct ? "check" : "alert", 16)} ${heading}</div>
      <div>${escapeHtml(evaluation.feedback_text || "")}</div>
      ${
        evaluation.misconception_tag
          ? `<div style="margin-top:8px;font-size:var(--text-xs);opacity:.85">Misconception spotted: ${escapeHtml(
              evaluation.misconception_tag
            )}</div>`
          : ""
      }`;
    dom.feedback.hidden = false;

    // Mark the chosen MCQ option so the answer stays visible while reading feedback.
    if (state.selectedOption) {
      [...dom.options.children].forEach((child) => {
        if (child.dataset.value === state.selectedOption) {
          child.classList.add(evaluation.correct ? "correct" : "incorrect");
        }
      });
    }

    dom.submitAnswer.textContent = "Submit answer";
    state.question = null;
    // The card stays up until the lesson moves on, so the learner reads the
    // feedback at their own pace rather than racing a timer.
  }

  function dismissCheckpoint() {
    dom.checkpoint.hidden = true;
    dom.feedback.hidden = true;
    state.question = null;
    state.selectedOption = null;
  }

  /* ---------------------------------------------------------------------
     Chapter notes
     --------------------------------------------------------------------- */

  const GREEK = {
    "\\Sigma": "Σ", "\\sum": "Σ", "\\Delta": "Δ", "\\delta": "δ", "\\alpha": "α",
    "\\beta": "β", "\\theta": "θ", "\\pi": "π", "\\mu": "μ", "\\omega": "ω",
    "\\cdot": "·", "\\times": "×", "\\div": "÷", "\\pm": "±", "\\approx": "≈",
    "\\leq": "≤", "\\geq": "≥", "\\neq": "≠", "\\rightarrow": "→", "\\infty": "∞",
  };

  /** Turn LaTeX into readable plain text — a backslash must never reach the page. */
  function plainMath(raw) {
    let s = String(raw || "").trim();
    s = s.replace(/```[a-z]*|```/g, "").replace(/^latex:\s*/i, "");
    s = s.replace(/\\\\/g, "\\");
    s = s.replace(/^\$\$|\$\$$/g, "").replace(/^\$|\$$/g, "");
    s = s.replace(/\\\((.*?)\\\)/gs, "$1").replace(/\\\[(.*?)\\\]/gs, "$1");
    s = s.replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "($1)/($2)");
    s = s.replace(/\\vec\s*\{([^{}]*)\}/g, "$1⃗").replace(/\\(?:text|mathrm)\s*\{([^{}]*)\}/g, "$1");
    for (const [tex, glyph] of Object.entries(GREEK)) s = s.split(tex).join(glyph);
    s = s.replace(/\\[a-zA-Z]+/g, "").replace(/[{}]/g, "");
    return s.replace(/\s+/g, " ").trim();
  }

  /** First sentences of the script, used when the model returned no notes. */
  function sentenceFallback(script) {
    return String(script || "")
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 4);
  }

  function showChapterNotes(payload) {
    const notes = payload.notes || {};
    dom.notesConcept.textContent = payload.concept || payload.title || "This concept";

    dom.notesDepth.textContent = payload.depth || "";
    dom.notesDepth.hidden = !payload.depth;
    dom.notesMinutes.textContent = payload.est_minutes ? `${payload.est_minutes} min` : "";
    dom.notesMinutes.hidden = !payload.est_minutes;

    const visual = payload.visual_spec || {};
    const formula =
      visual.type === "equation" && typeof visual.content === "string"
        ? plainMath(visual.content)
        : "";
    dom.notesFormula.textContent = formula;
    dom.notesFormula.hidden = !formula;

    const points = (notes.key_points || []).filter(Boolean);
    const bullets = points.length ? points : sentenceFallback(payload.script_text);
    clear(dom.notesPoints);
    bullets.forEach((point) => dom.notesPoints.appendChild(el("li", {}, point)));

    dom.notesExample.textContent = notes.example || "";
    dom.notesExampleWrap.hidden = !notes.example;

    dom.notesTranscript.textContent = payload.script_text || "";
    dom.notes.hidden = false;
  }

  /* ---------------------------------------------------------------------
     Adaptation status — one banner mapped 1:1 to the backend's own decision.
     --------------------------------------------------------------------- */

  const ADAPTATION_COPY = {
    MODIFY: {
      kind: "modify",
      text: "Let's try another explanation.",
      spinning: true,
    },
    REGENERATE: {
      kind: "regenerate",
      text: "Let's rethink this topic and create a new explanation.",
      spinning: true,
    },
    HUMAN: {
      kind: "human",
      text: "Your mentor has been notified.",
      spinning: false,
      icon: "🧑‍🏫",
    },
  };

  function showAdaptationBanner(action, key) {
    const copy = ADAPTATION_COPY[action];
    if (!copy) {
      hideAdaptationBanner();
      return;
    }
    // Keyed by node + action so a WS reconnect or resend can't stack a second
    // identical banner on top of the one already shown.
    if (state.lastAdaptationKey === key) return;
    state.lastAdaptationKey = key;

    dom.adaptationBanner.dataset.kind = copy.kind;
    dom.adaptationText.textContent = copy.text;
    dom.adaptationSpinner.hidden = !copy.spinning;
    dom.adaptationIcon.hidden = !copy.icon;
    dom.adaptationIcon.textContent = copy.icon || "";
    dom.adaptationBanner.hidden = false;

    clearTimeout(state.adaptationTimeout);
    // A MODIFY/REGENERATE reply that never arrives must not leave the student
    // staring at "Let's try another explanation" forever with no signal.
    if (copy.spinning) {
      state.adaptationTimeout = setTimeout(() => {
        if (state.lastAdaptationKey === key) {
          dom.adaptationText.textContent = "Still working on this — hang tight…";
        }
      }, 20000);
    }
  }

  function hideAdaptationBanner() {
    state.lastAdaptationKey = null;
    clearTimeout(state.adaptationTimeout);
    dom.adaptationBanner.hidden = true;
  }

  /** Keep one entry per concept so the class notes build up as it is taught. */
  function collectNotes(payload) {
    const points = (payload.notes?.key_points || []).filter(Boolean);
    const entry = {
      node_id: payload.node_id,
      concept: payload.concept || payload.title || "Concept",
      key_points: points.length ? points : sentenceFallback(payload.script_text).slice(0, 3),
      example: payload.notes?.example || "",
    };
    // A re-taught concept replaces its earlier notes rather than duplicating it.
    const at = state.collectedNotes.findIndex((n) => n.node_id === entry.node_id);
    if (at >= 0) state.collectedNotes[at] = entry;
    else state.collectedNotes.push(entry);
    renderLessonNotes();
  }

  function renderLessonNotes() {
    clear(dom.lessonNotesList);
    state.collectedNotes.forEach((entry, index) => {
      const block = el("div", { style: index ? "margin-top:var(--sp-4)" : "" });
      block.append(
        el("div", { style: "font-weight:650;font-size:var(--text-sm)" }, `${index + 1}. ${entry.concept}`)
      );
      const list = el("ul", { style: "margin:4px 0 0;padding-left:1.1rem;line-height:1.6;font-size:var(--text-sm)" });
      entry.key_points.forEach((point) => list.append(el("li", {}, point)));
      block.append(list);
      if (entry.example) {
        block.append(
          el("p", { class: "subtle", style: "margin:6px 0 0;font-size:var(--text-sm)" }, `Example: ${entry.example}`)
        );
      }
      dom.lessonNotesList.append(block);
    });
    dom.lessonNotes.hidden = state.collectedNotes.length === 0;
  }

  /** After a reload, the notes already taught come back from the server. */
  async function restoreNotes() {
    try {
      const saved = await api.lessonNotes(lessonId);
      state.collectedNotes = (saved.notes || []).map((n) => ({
        node_id: n.node_id,
        concept: n.concept,
        key_points: (n.key_points || []).length
          ? n.key_points
          : sentenceFallback(n.script_text).slice(0, 3),
        example: n.example || "",
      }));
      renderLessonNotes();
    } catch {
      // Notes are a convenience; a failed restore must not stop the lesson.
    }
  }

  dom.downloadNotes.addEventListener("click", async () => {
    dom.downloadNotes.disabled = true;
    try {
      await api.downloadNotes(lessonId, dom.title.textContent);
      toast("Notes saved to your downloads.", "success");
    } catch (error) {
      toast(`Couldn't download your notes: ${error.message}`, "error");
    } finally {
      dom.downloadNotes.disabled = false;
    }
  });

  /* ---------------------------------------------------------------------
     Video
     --------------------------------------------------------------------- */

  /** No playable video for this segment: the text explanation stands in, and
   *  the lesson must not wait on a video that will never end. */
  function segmentWithoutVideo(title, body) {
    dom.video.hidden = true;
    showOverlay(title, body);
    markWatched(); // the server then asks this concept's questions directly
  }

  async function playSegment(payload) {
    // Claimed before the (async) download, so a question arriving meanwhile
    // waits for THIS video rather than the previous, already-ended one.
    const segment = {
      node_id: payload.node_id,
      video_url: payload.video_url,
      checkpoints: [...(payload.checkpoints || [])].sort((a, b) => a.at_sec - b.at_sec),
      passed: new Set(payload.passed || []),
      awaiting: null,
      done: false,
      sent: false,
    };
    state.playing = segment;

    if (!payload.video_url) {
      segmentWithoutVideo(payload.title || "Concept", payload.script_text || "");
      return;
    }

    try {
      // Media is owner-scoped and needs an Authorization header, so it is
      // fetched as a blob rather than set directly as the video src.
      const objectUrl = await api.mediaObjectUrl(payload.video_url);
      if (state.playing !== segment) {
        URL.revokeObjectURL(objectUrl); // a newer segment arrived meanwhile
        return;
      }
      state.objectUrls.forEach((url) => URL.revokeObjectURL(url));
      state.objectUrls = [objectUrl];

      dom.video.onerror = () => {
        if (state.playing !== segment) return;
        console.warn("Video failed to play, displaying concept notes and card instead.");
        segmentWithoutVideo(payload.title || "Concept", payload.script_text || "");
        toast("Video playback encountered an error — displaying lesson notes.", "warning", 5000);
      };
      dom.video.src = objectUrl;
      // Coming back to a half-watched video: continue after the last
      // question already answered rather than from 0:00.
      const resumeAt = Math.max(
        0,
        ...segment.checkpoints.filter((cp) => segment.passed.has(cp.index)).map((cp) => cp.at_sec)
      );
      if (resumeAt > 0) {
        dom.video.addEventListener("loadedmetadata", () => { dom.video.currentTime = resumeAt; }, { once: true });
      }
      dom.video.hidden = false;
      hideOverlay();
      setStatus("Teaching");

      if (rewatch.open) {
        rewatch.resumeLive = true; // start it once the learner closes the rewatch
      } else {
        try {
          await dom.video.play();
        } catch {
          // Autoplay with sound is blocked until the learner interacts.
          toast("Tap play to start the lesson audio.", "info", 5000);
        }
      }
    } catch (error) {
      if (state.playing !== segment) return;
      segmentWithoutVideo("Playing without video", payload.script_text || "");
      toast(`Couldn't load the video: ${error.message}`, "error");
    }
  }

  /* ---------------------------------------------------------------------
     WebSocket
     --------------------------------------------------------------------- */

  /** Returns whether the message actually went out. */
  function send(eventType, payload) {
    if (state.socket?.readyState === WebSocket.OPEN) {
      state.socket.send(JSON.stringify({ event_type: eventType, payload }));
      return true;
    }
    return false;
  }

  const HANDLERS = {
    session_ready(payload) {
      dom.title.textContent = payload.title;
      document.title = `${payload.title} — Shikshak AI`;
      log(payload.resumed ? "Resumed your lesson where you left off" : "Lesson started");
      if (payload.resumed) {
        toast("Resuming from where you left off.", "info");
        restoreNotes();
      }
    },

    curriculum_loaded(payload) {
      // Keep statuses already known (a snapshot can arrive before this).
      const known = new Map(state.nodes.map((n) => [n.node_id, n]));
      state.nodes = (payload.nodes || []).map((n) => ({
        status: "pending", attempts: 0, ...(known.get(n.node_id) || {}), ...n,
        ...(known.has(n.node_id) ? { status: known.get(n.node_id).status } : {}),
      }));
      renderNodes();
      log(`Curriculum loaded — ${state.nodes.length} concepts`);
    },

    lesson_plan_update(payload) {
      state.nodes = (payload.nodes || []).map((n) => ({ ...n, status: "pending", attempts: 0 }));
      renderNodes();
      toast("The lesson plan was rebuilt around what you're finding hard.", "info", 6000);
      log("Lesson plan regenerated");
    },

    progress_snapshot: applySnapshot,

    ai_state(payload) {
      const labels = {
        PLAN: "Planning",
        TEACH: "Teaching",
        INTERACT: "Asking you a question",
        EVALUATE: "Grading your answer",
        ASSESS: "Writing your report",
        RESUME: "Picking up where you left off",
      };
      setStatus(labels[payload.state] || payload.state);
      if (payload.node_id) {
        state.currentNodeId = payload.node_id;
        renderNodes();
      }
      if (payload.state === "TEACH") {
        showOverlay(payload.concept || "Preparing the next concept", "Writing the explanation…");
      }
    },

    explanation_chunk(payload) {
      state.currentNodeId = payload.node_id;
      showChapterNotes(payload);
      collectNotes(payload);
      // After a reconnect the server replays the concept already on screen:
      // keep the video, the question card and anything typed exactly as is.
      if (payload.replay && state.playing?.node_id === payload.node_id) {
        log(`Reconnected — continuing ${payload.concept}`);
        return;
      }
      dismissCheckpoint();
      hideAdaptationBanner();
      showOverlay(
        payload.concept || "",
        payload.replay ? "Loading this concept…" : "Rendering the video for this concept…"
      );
      log(`Explaining: ${payload.concept}`);
    },

    render_started() {
      showOverlay(
        "Rendering this concept",
        "Generating narration, lip-sync and the visual board. This takes about 30 seconds."
      );
      setStatus("Rendering");
    },

    video_segment(payload) {
      const current = state.playing;
      if (current && current.node_id === payload.node_id && current.video_url === payload.video_url) {
        // A reconnect replayed the video already loaded: don't restart it.
        // Re-send whatever the new connection must hear from us.
        (payload.passed || []).forEach((i) => current.passed.add(i));
        if (current.awaiting != null && !state.question) {
          send("checkpoint_reached", { node_id: current.node_id, index: current.awaiting });
        } else if (current.done) {
          current.sent = false;
          markWatched();
        }
        return;
      }
      log(`Video ready (${formatSeconds(payload.duration_sec)})`);
      playSegment(payload);
    },

    render_failed(payload) {
      log(`Render failed: ${payload.reason}`);
      toast("Video rendering failed for this concept — continuing with the written explanation.", "error", 7000);
      state.playing = { node_id: payload.node_id, video_url: null, done: false, sent: false };
      segmentWithoutVideo("Continuing without video", payload.reason || "");
    },

    answer_rejected(payload) {
      toast(payload.reason || "Please enter an answer.", "warning");
      resetSubmit();
    },

    citation_updated(payload) {
      // Provenance comes from retrieval metadata, so it names the file, the
      // page or section, and how well grounded this concept actually was.
      if (!payload.excerpt) {
        dom.citationText.innerHTML =
          '<span class="subtle">No matching document context — teaching this concept from general knowledge.</span>';
        dom.citation.hidden = false;
        return;
      }

      const where = [
        payload.section_title,
        payload.page_or_slide ? `page ${payload.page_or_slide}` : "",
      ].filter(Boolean).join(" · ");

      const weak = payload.risk_level && payload.risk_level !== "low";
      dom.citationText.innerHTML = `
        <span class="badge ${weak ? "badge-amber" : "badge-green"}" style="margin-bottom:6px">
          ${weak ? "Loosely grounded" : "Grounded in your material"}
        </span>
        <span style="display:block;font-weight:600;margin-top:6px">${escapeHtml(
          payload.source_title || "Your document"
        )}${where ? ` — ${escapeHtml(where)}` : ""}</span>
        <span style="display:block;margin-top:6px">${escapeHtml(payload.excerpt)}</span>
        ${
          payload.chunk_count
            ? `<span class="subtle" style="display:block;margin-top:6px">${payload.chunk_count} passage${
                payload.chunk_count === 1 ? "" : "s"
              } used for this concept</span>`
            : ""
        }
        ${
          payload.attempts > 1
            ? `<span class="subtle" style="display:block;margin-top:4px">
                 First search was weakly grounded — refined to
                 <strong>${escapeHtml(payload.refined_query || "")}</strong> and searched again.
               </span>`
            : ""
        }`;
      dom.citation.hidden = false;
    },

    interaction_event(payload) {
      const id = payload.interaction_id;
      if (id && state.question?.interaction_id === id && !dom.checkpoint.hidden) {
        // Re-asked after a reconnect: keep the card and the typed answer. If it
        // was mid-"Grading…", the answer never arrived, so allow a resubmit.
        resetSubmit();
        return;
      }
      // The video waits at this question until it has been answered.
      const seg = state.playing;
      if (seg && payload.node_id === seg.node_id && payload.checkpoint_index != null) {
        const cp = seg.checkpoints.find((c) => c.index === payload.checkpoint_index);
        seg.awaiting = payload.checkpoint_index;
        dom.video.pause();
        if (cp && !dom.video.hidden && Math.abs(dom.video.currentTime - cp.at_sec) > 0.5) {
          dom.video.currentTime = cp.at_sec;
        }
      }
      dismissCheckpoint();
      resetSubmit();
      setStatus("Your turn");
      showQuestion(payload);
      log(`Question asked: ${payload.question_text.slice(0, 70)}`);
    },

    resume_video(payload) {
      if (state.playing?.node_id === payload.node_id && payload.index != null) {
        resumeAfterCheckpoint(payload.index);
      }
    },

    evaluation_result(payload) {
      state.grading = false;
      showFeedback(payload);
      log(`Graded: ${payload.correct ? "correct" : `partial ${payload.partial_credit}`}`);
    },

    adaptation_decision(payload) {
      log(`Adaptation: ${payload.action} — ${payload.reason}`);
      if (payload.action === "ALLOW") {
        hideAdaptationBanner();
        return;
      }
      showAdaptationBanner(payload.action, `${payload.target_node_id || state.currentNodeId}:${payload.action}`);
    },

    assessment_report(payload) {
      log(`Lesson complete — ${payload.score_pct}%`);
      state.closedByUs = true;
      showOverlay("Lesson complete", `You scored ${payload.score_pct}%. Opening your report…`);
      setTimeout(() => {
        window.location.href = `/report.html?lesson=${encodeURIComponent(lessonId)}`;
      }, 1800);
    },

    human_escalation(payload) {
      state.closedByUs = true;
      // The lesson stops here for a human teacher: the video can't be played on.
      state.lessonStopped = true;
      dom.video.pause();
      dom.video.controls = false;
      setStatus("Paused");
      showAdaptationBanner("HUMAN", `${state.currentNodeId}:HUMAN`);
      // The HUMAN copy is fixed regardless of whether the email actually sent
      // (e.g. no mentor on file) — the student's experience is the same
      // either way, and the mentor-notified detail is for the mentor, not them.
      dom.checkpoint.hidden = true;
      log(payload.mentor_notified ? "Escalated — mentor notified by email" : "Escalated to a human teacher");
      showPaused(payload.escalation);
    },

    review_needed(payload) {
      log(`${payload.concepts.length} concept(s) still to review`);
      showReviewNeeded(payload.concepts || []);
    },

    lesson_paused(payload) {
      log("This lesson is paused for your mentor");
      showPaused(payload.escalation);
    },

    pong() {},
  };

  // Close codes after which reconnecting cannot help.
  const CLOSE_SUPERSEDED = 4001; // this lesson was opened in another tab
  const CLOSE_POLICY = 1008; // bad ticket, account or lesson

  /** Reconnect quietly with backoff. The server resumes exactly where the
   *  lesson was, and the video keeps playing meanwhile. */
  function scheduleReconnect() {
    if (state.closedByUs || state.reconnectTimer) return;
    state.reconnectAttempts += 1;
    if (state.reconnectAttempts > MAX_RECONNECT_ATTEMPTS) {
      setConnection("Offline", "badge-rose");
      showOverlay(
        "Can't reach your classroom",
        "Your progress is saved. Check your internet connection, then reload this page."
      );
      return;
    }
    const delay = Math.min(15000, 1000 * 2 ** (state.reconnectAttempts - 1));
    setConnection("Reconnecting…", "badge-amber");
    log(`Connection lost — reconnecting in ${Math.round(delay / 1000)}s (your progress is saved)`);
    state.reconnectTimer = setTimeout(() => {
      state.reconnectTimer = null;
      connect();
    }, delay);
  }

  function connect() {
    setConnection(state.reconnectAttempts ? "Reconnecting…" : "Connecting", state.reconnectAttempts ? "badge-amber" : "");

    openLessonSocket(lessonId)
      .then((socket) => {
        state.socket = socket;

        socket.onopen = () => {
          setConnection("Live", "badge-green");
          log(state.reconnectAttempts ? "Reconnected" : "Connected to your classroom");
          if (state.reconnectAttempts) toast("Reconnected — continuing your lesson.", "success", 2500);
          state.reconnectAttempts = 0;
        };

        socket.onmessage = (event) => {
          let message;
          try {
            message = JSON.parse(event.data);
          } catch {
            return;
          }

          if (message.error) {
            // The close that follows decides whether to reconnect; the error
            // itself must not cover a video the learner is watching.
            state.lastError = message.error;
            toast(message.error, "error", 8000);
            log(`Error: ${message.error}`);
            return;
          }

          HANDLERS[message.event_type]?.(message.payload || {});
        };

        socket.onclose = (event) => {
          if (state.socket !== socket || state.closedByUs) return;
          state.socket = null;
          if (event.code === CLOSE_SUPERSEDED) {
            state.closedByUs = true;
            setConnection("Open elsewhere", "badge-rose");
            showOverlay(
              "This lesson is open in another tab",
              "Continue there, or reload this page to continue here."
            );
            return;
          }
          if (event.code === CLOSE_POLICY) {
            setConnection("Unavailable", "badge-rose");
            showOverlay("Couldn't continue the lesson", state.lastError || "Please reload this page.");
            return;
          }
          scheduleReconnect();
        };

        socket.onerror = () => setConnection("Connection problem", "badge-rose");
      })
      .catch((error) => {
        // 4xx (lesson gone, not planned, signed out) won't fix itself; a
        // network failure or 5xx usually will.
        if (error.status >= 400 && error.status < 500) {
          setConnection("Couldn't connect", "badge-rose");
          showOverlay("Couldn't start the lesson", error.message);
          toast(error.message, "error", 8000);
          return;
        }
        scheduleReconnect();
      });
  }

  // Back online: don't wait out the backoff.
  window.addEventListener("online", () => {
    if (!state.socket && state.reconnectTimer && !state.closedByUs) {
      clearTimeout(state.reconnectTimer);
      state.reconnectTimer = null;
      connect();
    }
  });

  // Load the persisted lesson first, so the rail is populated even before
  // the socket has produced anything.
  try {
    const lesson = await api.getLesson(lessonId);
    dom.title.textContent = lesson.title;
    document.title = `${lesson.title} — Shikshak AI`;
    state.nodes = lesson.nodes || [];
    dom.progressLabel.textContent = `${lesson.nodes_completed} / ${lesson.node_count}`;
    dom.progressBar.style.width = `${lesson.progress_pct}%`;
    renderNodes();

    if (lesson.status === "completed") {
      window.location.replace(`/report.html?lesson=${encodeURIComponent(lessonId)}`);
    } else if (lesson.status === "escalated") {
      showPaused(lesson.escalation); // never auto-start a paused lesson
    } else {
      connect();
    }
  } catch (error) {
    showOverlay(
      "Lesson expired or not found",
      `${error.message}. If the server recently restarted, previous lessons reset. Redirecting to New Lesson…`
    );
    setConnection("Unavailable", "badge-rose");
    toast("Lesson not found on server. Taking you to start a fresh lesson…", "warning", 5000);
    setTimeout(() => {
      window.location.replace("/new-lesson.html");
    }, 3000);
  }

  // Keep the socket alive through proxy idle timeouts on long renders.
  const heartbeat = setInterval(() => send("ping", {}), 25000);

  window.addEventListener("beforeunload", () => {
    clearInterval(heartbeat);
    state.objectUrls.forEach((url) => URL.revokeObjectURL(url));
    state.closedByUs = true;
    state.socket?.close();
  });
}
