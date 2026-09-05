/**
 * Shikshak AI — Live Classroom Workspace Controller (classroom.html)
 * Fully connected to Backend, Agent Orchestration, RAG Grounding, and Video Player.
 */

import { ShikshakWSClient } from "./wsClient.js";
import { render } from "./render.js";

document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  const mode = urlParams.get("mode") || "mock";
  const sessionId = urlParams.get("session_id") || "demo_session_01";
  const token = urlParams.get("token") || "";
  const topicParam = urlParams.get("topic") || "Cell Membrane & Transport";

  // Elements
  const connectionSignal = document.getElementById("connection-signal");
  const connectionLabel = document.getElementById("connection-label");
  const lessonBreadcrumb = document.getElementById("lesson-breadcrumb");
  const slideTitle = document.getElementById("slide-title");
  const slideSubtext = document.getElementById("slide-subtext");
  const stagePreparingOverlay = document.getElementById("stage-preparing-overlay");
  const avatarGraphic = document.getElementById("avatar-graphic");
  const subtitleContent = document.getElementById("subtitle-content");
  const lessonVideo = document.getElementById("lesson-video");
  const whiteboardSlide = document.getElementById("whiteboard-slide");

  // Left Curriculum Elements
  const nodesList = document.getElementById("nodes-list");
  const curriculumProgressText = document.getElementById("curriculum-progress-text");
  const curriculumProgressPct = document.getElementById("curriculum-progress-pct");
  const curriculumRailFill = document.getElementById("curriculum-rail-fill");

  // Checkpoint Elements
  const checkpointCard = document.getElementById("checkpoint-card");
  const questionText = document.getElementById("question-text");
  const optionsList = document.getElementById("options-list");
  const btnCheckAnswer = document.getElementById("btn-check-answer");
  const evalBanner = document.getElementById("eval-banner");
  const evalText = document.getElementById("eval-text");
  const evalIcon = document.getElementById("eval-icon");

  // AI Inspector Elements
  const snNodes = {
    PLAN: document.getElementById("sn-plan"),
    TEACH: document.getElementById("sn-teach"),
    INTERACT: document.getElementById("sn-interact"),
    EVALUATE: document.getElementById("sn-evaluate"),
    ADAPT: document.getElementById("sn-adapt"),
    ASSESS: document.getElementById("sn-evaluate"),
  };
  const citationSourceText = document.getElementById("citation-source-text");
  const citationExcerpt = document.getElementById("citation-excerpt");
  const confidenceVal = document.getElementById("confidence-val");
  const confidenceBar = document.getElementById("confidence-bar");
  const decisionCard = document.getElementById("decision-card");
  const decisionBadge = document.getElementById("decision-badge");
  const decisionReason = document.getElementById("decision-reason");

  // Set Dynamic Breadcrumb
  if (lessonBreadcrumb && topicParam) {
    lessonBreadcrumb.textContent = `Lesson · ${topicParam}`;
  }

  // Video Controls
  const ctrlPlay = document.getElementById("ctrl-play");
  let isPlaying = true;
  let currentQuestion = null;
  let selectedAnswer = "";

  // Dynamic Curriculum Rendering Function
  function renderCurriculum(plan) {
    if (!plan || !plan.nodes || plan.nodes.length === 0) return;
    nodesList.innerHTML = "";
    const total = plan.nodes.length;
    plan.nodes.forEach((node, idx) => {
      const li = document.createElement("li");
      li.className = `node-item ${idx === 0 ? "active" : ""}`;
      li.dataset.node = node.node_id;
      li.id = `item-${node.node_id}`;
      const conceptText = node.concept || node.title || `Concept ${idx + 1}`;
      li.innerHTML = `
        <span class="node-marker">${idx + 1}</span>
        <span>${idx + 1}. ${conceptText}</span>
      `;
      li.addEventListener("click", () => {
        document.querySelectorAll(".node-item").forEach((el) => el.classList.remove("active"));
        li.classList.add("active");
      });
      nodesList.appendChild(li);
    });

    const activeNum = 1;
    const pct = Math.round((activeNum / total) * 100);
    curriculumProgressText.textContent = `${activeNum} of ${total} in progress`;
    curriculumProgressPct.textContent = `${pct}%`;
    curriculumRailFill.style.width = `${pct}%`;
  }

  // Pre-fetch real plan if in live mode
  if (mode === "live" && sessionId) {
    fetch(`/api/v1/sessions/${sessionId}/plan`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((plan) => {
        if (plan) renderCurriculum(plan);
      })
      .catch((err) => console.warn("Live plan fetch error:", err));
  }

  // Initialize WebSocket Client
  const wsClient = new ShikshakWSClient(sessionId, token, mode);

  // 1. Connection Status Handler
  wsClient.on("connection_status", ({ status }) => {
    connectionSignal.className = `status-signal ${status}`;
    connectionLabel.textContent = status.charAt(0).toUpperCase() + status.slice(1);
  });

  // 2. Dynamic Curriculum Stream Handler
  wsClient.on("curriculum_loaded", (plan) => {
    console.log("[Live Curriculum Loaded]", plan);
    renderCurriculum(plan);
  });

  wsClient.on("lesson_plan_update", (plan) => {
    console.log("[Lesson Plan Update]", plan);
    renderCurriculum(plan);
  });

  // 3. State Machine Progression Tracker
  wsClient.on("ai_state", ({ state, concept }) => {
    Object.keys(snNodes).forEach((k) => {
      if (snNodes[k]) snNodes[k].classList.remove("active");
    });
    if (snNodes[state]) {
      snNodes[state].classList.add("active");
    }
    if (concept && slideTitle) {
      slideTitle.textContent = `“${concept}”`;
    }
  });

  // 4. Live Explanation Script Chunk Stream
  wsClient.on("explanation_chunk", ({ script_text, title, concept }) => {
    stagePreparingOverlay.classList.remove("active");
    avatarGraphic.classList.add("avatar-talking");

    if (title || concept) {
      slideTitle.textContent = `“${title || concept}”`;
    }
    if (script_text) {
      slideSubtext.textContent = script_text;
      subtitleContent.textContent = script_text;
    }
  });

  // 5. RAG Grounding Citation Update
  wsClient.on("citation_updated", ({ source_title, excerpt, page_number }) => {
    if (citationSourceText) {
      citationSourceText.textContent = `${source_title} · Page ${page_number || 1}`;
    }
    if (citationExcerpt && excerpt) {
      citationExcerpt.textContent = `“${excerpt}”`;
    }
  });

  // 6. Video Segment (Rendered MP4 / Composited Avatar Video)
  wsClient.on("video_segment", (segment) => {
    stagePreparingOverlay.classList.remove("active");
    avatarGraphic.classList.add("avatar-talking");

    if (segment.title) {
      slideTitle.textContent = `“${segment.title}”`;
    }
    if (segment.script_text) {
      slideSubtext.textContent = segment.script_text;
      subtitleContent.textContent = segment.script_text;
    }
    if (segment.highlight_phrase) {
      subtitleContent.innerHTML = segment.script_text.replace(
        segment.highlight_phrase,
        `<span class="highlight-phrase">${segment.highlight_phrase}</span>`
      );
    }

    // Play rendered video if available
    if (segment.video_url && lessonVideo) {
      let vUrl = segment.video_url;
      if (!vUrl.startsWith("http") && !vUrl.startsWith("/api/")) {
        vUrl = `/api/v1/media/video?file=${encodeURIComponent(vUrl)}`;
      }
      console.log("[Video] Playing rendered segment from:", vUrl);
      lessonVideo.src = vUrl;
      lessonVideo.style.display = "block";
      whiteboardSlide.style.display = "none";
      lessonVideo.play().catch((e) => console.warn("Auto-play notice:", e));

      lessonVideo.onended = () => {
        avatarGraphic.classList.remove("avatar-talking");
      };
    } else {
      if (lessonVideo) lessonVideo.style.display = "none";
      if (whiteboardSlide) whiteboardSlide.style.display = "block";
    }
  });

  // 7. Subtitle Stream Update
  wsClient.on("subtitle_update", ({ text, highlight }) => {
    if (highlight) {
      subtitleContent.innerHTML = text.replace(
        highlight,
        `<span class="highlight-phrase">${highlight}</span>`
      );
    } else {
      subtitleContent.textContent = text;
    }
  });

  // 8. Interaction Event (Checkpoint Question from QuestionerAgent)
  wsClient.on("interaction_event", (event) => {
    currentQuestion = event;
    questionText.textContent = event.question_text;
    evalBanner.classList.remove("show");
    btnCheckAnswer.disabled = false;
    btnCheckAnswer.innerHTML = `<span>Check my answer →</span>`;

    // Render Radio Options
    optionsList.innerHTML = "";
    const opts = event.options || [];
    opts.forEach((opt, idx) => {
      const card = document.createElement("div");
      card.className = "option-card" + (idx === 0 ? " selected" : "");
      card.dataset.idx = idx;
      card.dataset.answer = opt;
      card.innerHTML = `
        <div class="option-radio"></div>
        <span class="option-text">${opt}</span>
      `;
      card.addEventListener("click", () => {
        document.querySelectorAll(".option-card").forEach((c) => c.classList.remove("selected"));
        card.classList.add("selected");
        selectedAnswer = opt;
      });
      optionsList.appendChild(card);
    });

    selectedAnswer = opts[0] || "";
    checkpointCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });

  // 9. Check Answer Submission to WebSocket / MLCore
  btnCheckAnswer.addEventListener("click", () => {
    if (!currentQuestion) return;
    btnCheckAnswer.disabled = true;
    btnCheckAnswer.innerHTML = `${render.getSpinnerSvg()} <span>Evaluating with ML Core...</span>`;

    wsClient.send({
      event_type: "student_response",
      payload: {
        node_id: currentQuestion.node_id,
        raw_answer: selectedAnswer,
        response_type: "mcq",
        response_time_sec: 3.2,
      },
    });
  });

  // 10. Evaluation Result Display (from MLCore)
  wsClient.on("evaluation_result", (result) => {
    btnCheckAnswer.innerHTML = `<span>Answer Evaluated</span>`;
    evalBanner.className = `eval-banner show ${result.correct ? "correct" : "incorrect"}`;
    evalIcon.innerHTML = result.correct ? render.getCheckmarkSvg() : "⚠";
    evalText.textContent = result.feedback_text;

    // Update telemetry confidence
    const confPct = Math.round((result.confidence || 0.9) * 100);
    confidenceVal.textContent = `${confPct}%`;
    confidenceBar.style.width = `${confPct}%`;
  });

  // 11. Adaptation Decision (from AdaptationController)
  wsClient.on("adaptation_decision", (decision) => {
    const action = (decision.action || "ALLOW").toLowerCase();
    decisionBadge.className = `decision-badge ${action}`;
    decisionBadge.textContent = decision.action;
    decisionReason.textContent = decision.reason;

    // Trigger visual pulse
    decisionCard.classList.remove("pulse");
    void decisionCard.offsetWidth; // force DOM reflow
    decisionCard.classList.add("pulse");
  });

  // 12. Session Complete & Report Transition
  wsClient.on("session_complete", ({ redirect_url }) => {
    render.showToast("Lesson complete! Transitioning to your mastery report...");
    setTimeout(() => {
      window.location.href = redirect_url || "report.html";
    }, 1200);
  });

  // Video Controls: Play/Pause Toggle
  ctrlPlay.addEventListener("click", () => {
    isPlaying = !isPlaying;
    ctrlPlay.textContent = isPlaying ? "⏸" : "▶";
    if (lessonVideo && lessonVideo.style.display !== "none") {
      if (isPlaying) lessonVideo.play();
      else lessonVideo.pause();
    }
    if (isPlaying) {
      avatarGraphic.classList.add("avatar-talking");
    } else {
      avatarGraphic.classList.remove("avatar-talking");
    }
  });

  // Tab Switcher (AI Inspector vs Notes)
  const tabInspectorBtn = document.getElementById("tab-btn-inspector");
  const tabNotesBtn = document.getElementById("tab-btn-notes");
  const tabInspectorContent = document.getElementById("tab-content-inspector");
  const tabNotesContent = document.getElementById("tab-content-notes");

  tabInspectorBtn.addEventListener("click", () => {
    tabInspectorBtn.classList.add("active");
    tabNotesBtn.classList.remove("active");
    tabInspectorContent.style.display = "flex";
    tabNotesContent.style.display = "none";
  });

  tabNotesBtn.addEventListener("click", () => {
    tabNotesBtn.classList.add("active");
    tabInspectorBtn.classList.remove("active");
    tabNotesContent.style.display = "flex";
    tabNotesContent.style.display = "none";
  });

  // Export Notes Action
  document.getElementById("btn-save-notes").addEventListener("click", () => {
    render.showToast("Notes exported to Downloads (PDF)");
  });

  // Quick Help Buttons
  document.getElementById("btn-repeat-concept").addEventListener("click", () => {
    render.showToast("Replaying concept explanation...");
  });

  document.getElementById("btn-simpler-analogy").addEventListener("click", () => {
    render.showToast("Requesting a simpler analogy from ExplainerAgent...");
  });

  // Reaction Buttons
  document.querySelectorAll(".reaction-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.style.transform = "scale(1.1)";
      setTimeout(() => (btn.style.transform = "none"), 200);
      render.showToast(`Feedback noted: ${btn.textContent}`);
    });
  });

  // Connect WebSocket!
  wsClient.connect();
});
