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
    caption: $("#caption"),
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
     Video
     --------------------------------------------------------------------- */

  async function playSegment(payload) {
    dom.caption.innerHTML = `<strong>${escapeHtml(payload.title || "")}</strong><br>${escapeHtml(
      payload.script_text || ""
    )}`;

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
      if (payload.resumed) toast("Resuming from where you left off.", "info");
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
      state.currentNodeId = payload.node_id;
      dom.caption.innerHTML = `<strong>${escapeHtml(payload.title || "")}</strong><br>${escapeHtml(
        payload.script_text || ""
      )}`;
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
      dom.citationText.textContent = payload.excerpt || "";
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
      const messages = {
        ALLOW: "Moving on to the next concept.",
        MODIFY: "Re-teaching this concept a different way.",
        REGENERATE: "Rebuilding the rest of the lesson plan.",
        HUMAN: "Flagging this for a human teacher.",
      };
      log(`Adaptation: ${payload.action} — ${payload.reason}`);
      if (payload.action !== "ALLOW") toast(messages[payload.action], "info", 5000);
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
      showOverlay("This one needs a human teacher", payload.reason);
      dom.checkpoint.hidden = true;
      log("Escalated to a human teacher");
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
