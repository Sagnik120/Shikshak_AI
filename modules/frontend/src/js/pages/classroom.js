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
  };

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
    dom.overlay.hidden = false;
  }

  function hideOverlay() {
    dom.overlay.hidden = true;
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

      const mastered = node.status === "mastered";
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
      case "skipped":
        return "Moved on";
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

  dom.answerInput.addEventListener("input", () => {
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

    send("student_response", {
      node_id: state.question.node_id,
      raw_answer: answer,
      response_time_sec: (Date.now() - state.questionShownAt) / 1000,
    });

    dom.submitAnswer.disabled = true;
    dom.submitAnswer.textContent = "Grading…";
    dom.answerHint.textContent = "Shikshak is checking your understanding.";
    log(`Answer submitted: ${answer.slice(0, 60)}`);
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

  async function playSegment(payload) {
    if (!payload.video_url) {
      showOverlay(payload.title || "Concept", payload.script_text || "");
      return;
    }

    try {
      // Media is owner-scoped and needs an Authorization header, so it is
      // fetched as a blob rather than set directly as the video src.
      const objectUrl = await api.mediaObjectUrl(payload.video_url);
      state.objectUrls.push(objectUrl);

      dom.video.src = objectUrl;
      dom.video.hidden = false;
      hideOverlay();
      setStatus("Teaching");

      dom.video.onerror = () => {
        console.warn("Video failed to play, displaying concept notes and card instead.");
        dom.video.hidden = true;
        showOverlay(payload.title || "Concept", payload.script_text || "");
        toast("Video playback encountered an error — displaying lesson notes.", "warning", 5000);
      };

      try {
        await dom.video.play();
      } catch {
        // Autoplay with sound is blocked until the learner interacts.
        toast("Tap play to start the lesson audio.", "info", 5000);
      }
    } catch (error) {
      showOverlay("Playing without video", payload.script_text || "");
      toast(`Couldn't load the video: ${error.message}`, "error");
    }
  }

  /* ---------------------------------------------------------------------
     WebSocket
     --------------------------------------------------------------------- */

  function send(eventType, payload) {
    if (state.socket?.readyState === WebSocket.OPEN) {
      state.socket.send(JSON.stringify({ event_type: eventType, payload }));
    }
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
      state.nodes = (payload.nodes || []).map((n) => ({ ...n, status: "pending", attempts: 0 }));
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
      dismissCheckpoint();
      hideAdaptationBanner();
      state.currentNodeId = payload.node_id;
      showChapterNotes(payload);
      collectNotes(payload);
      showOverlay(payload.concept || "", "Rendering the video for this concept…");
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
      log(`Video ready (${formatSeconds(payload.duration_sec)})`);
      playSegment(payload);
    },

    render_failed(payload) {
      log(`Render failed: ${payload.reason}`);
      toast("Video rendering failed for this concept — continuing with the written explanation.", "error", 7000);
      showOverlay("Continuing without video", payload.reason || "");
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
      setStatus("Your turn");
      dismissCheckpoint();
      showQuestion(payload);
      log(`Question asked: ${payload.question_text.slice(0, 70)}`);
    },

    evaluation_result(payload) {
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
      setStatus("Paused");
      showAdaptationBanner("HUMAN", `${state.currentNodeId}:HUMAN`);
      // The HUMAN copy is fixed regardless of whether the email actually sent
      // (e.g. no mentor on file) — the student's experience is the same
      // either way, and the mentor-notified detail is for the mentor, not them.
      showOverlay("This one needs a human teacher", payload.reason);
      dom.checkpoint.hidden = true;
      log(payload.mentor_notified ? "Escalated — mentor notified by email" : "Escalated to a human teacher");
    },

    pong() {},
  };

  function connect() {
    setConnection("Connecting");

    openLessonSocket(lessonId)
      .then((socket) => {
        state.socket = socket;

        socket.onopen = () => {
          setConnection("Live", "badge-green");
          log("Connected to your classroom");
        };

        socket.onmessage = (event) => {
          let message;
          try {
            message = JSON.parse(event.data);
          } catch {
            return;
          }

          if (message.error) {
            toast(message.error, "error", 8000);
            showOverlay("Something went wrong", message.error);
            log(`Error: ${message.error}`);
            return;
          }

          HANDLERS[message.event_type]?.(message.payload || {});
        };

        socket.onclose = () => {
          setConnection("Disconnected", "badge-rose");
          if (!state.closedByUs) {
            log("Connection closed — your progress is saved");
            showOverlay(
              "Disconnected",
              "Your progress is saved. Reload this page to pick the lesson back up."
            );
          }
        };

        socket.onerror = () => setConnection("Connection problem", "badge-rose");
      })
      .catch((error) => {
        setConnection("Couldn't connect", "badge-rose");
        showOverlay("Couldn't start the lesson", error.message);
        toast(error.message, "error", 8000);
      });
  }

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
    } else {
      connect();
    }
  } catch (error) {
    showOverlay("Couldn't open this lesson", error.message);
    setConnection("Unavailable", "badge-rose");
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
