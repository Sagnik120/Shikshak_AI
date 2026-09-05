/**
 * Shikshak AI — Launchpad Controller (index.html)
 */

import { api } from "./api.js";
import { render } from "./render.js";

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const uploadSummary = document.getElementById("upload-summary");
  const uploadedFilename = document.getElementById("uploaded-filename");
  const uploadedFilesize = document.getElementById("uploaded-filesize");
  const topicInput = document.getElementById("topic-input");
  const suggestionPills = document.querySelectorAll(".suggestion-pill");
  const presetSelect = document.getElementById("preset-select");
  const actionStatusText = document.getElementById("action-status-text");
  const btnGenerate = document.getElementById("btn-generate");
  const generationPanel = document.getElementById("generation-panel");
  const progressFill = document.getElementById("progress-fill");

  // Stages
  const stage1 = document.getElementById("stage-1");
  const stage2 = document.getElementById("stage-2");
  const stage3 = document.getElementById("stage-3");

  // State
  let currentFile = null;
  let currentTopic = topicInput.value.trim();
  let currentLevel = "beginner";
  let currentBudget = "15";
  let currentLang = "en";
  let currentStyle = "visual";

  // Setup Rail Steps
  const stepSource = document.getElementById("step-source");
  const stepExplore = document.getElementById("step-explore");
  const stepTune = document.getElementById("step-tune");

  function updateStatusText() {
    if (currentFile) {
      actionStatusText.textContent = `Ready to build lesson from: ${currentFile.name}`;
      stepSource.classList.add("active");
      stepExplore.classList.remove("active");
    } else if (currentTopic) {
      actionStatusText.textContent = `Ready to build lesson: ${currentTopic}`;
      stepExplore.classList.add("active");
      stepSource.classList.remove("active");
    }
  }

  // 1. Drag & Drop File Upload
  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") fileInput.click();
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.add("drag-over");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  let activeSessionId = null;
  let activeToken = null;

  async function handleFileUpload(file) {
    currentFile = file;
    dropZone.style.display = "none";
    uploadedFilename.textContent = file.name;
    uploadedFilesize.textContent = `${render.formatBytes(file.size)} · Ingesting with RAG...`;
    uploadSummary.classList.add("show");
    render.showToast(`Uploading and indexing "${file.name}" with RAG...`);
    updateStatusText();

    try {
      if (!activeSessionId) {
        const session = await api.createSession();
        activeSessionId = session.session_id;
        activeToken = session.token;
      }
      const res = await api.uploadDocument(activeSessionId, file, activeToken);
      if (res && res.detected_structure && res.detected_structure.chapters) {
        uploadedFilesize.textContent = `${render.formatBytes(file.size)} · RAG Indexed (${res.detected_structure.chapters.length} sections)`;
        const chapterPillsContainer = document.querySelector(".chapter-pills");
        if (chapterPillsContainer && res.detected_structure.chapters.length > 0) {
          chapterPillsContainer.innerHTML = res.detected_structure.chapters
            .slice(0, 5)
            .map((ch) => `<span class="chapter-pill">${ch}</span>`)
            .join("");
        }
      }
    } catch (e) {
      console.warn("Upload ingestion error:", e);
    }
  }

  // 2. Topic Input & Suggestion Pills
  topicInput.addEventListener("input", () => {
    currentTopic = topicInput.value.trim();
    currentFile = null;
    suggestionPills.forEach((p) => p.classList.remove("selected"));
    updateStatusText();
  });

  suggestionPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      suggestionPills.forEach((p) => p.classList.remove("selected"));
      pill.classList.add("selected");
      currentTopic = pill.dataset.topic;
      topicInput.value = currentTopic;
      currentFile = null;
      updateStatusText();
    });
  });

  // 3. Preset Selector
  presetSelect.addEventListener("change", () => {
    const val = presetSelect.value;
    if (val === "cell_structure") {
      topicInput.value = "Cell Membrane & Transport";
    } else if (val === "newtons_laws") {
      topicInput.value = "Newton's Laws of Motion";
    } else if (val === "photosynthesis") {
      topicInput.value = "Photosynthesis & Light Reactions";
    } else if (val === "quadratics") {
      topicInput.value = "Quadratic Equations & Roots";
    }
    currentTopic = topicInput.value;
    currentFile = null;
    updateStatusText();
  });

  // 4. Segmented Controls (Level & Budget)
  document.querySelectorAll("#control-level .seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#control-level .seg-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentLevel = btn.dataset.value;
      stepTune.classList.add("active");
    });
  });

  document.querySelectorAll("#control-budget .seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#control-budget .seg-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentBudget = btn.dataset.value;
      stepTune.classList.add("active");
    });
  });

  // Select Dropdowns
  document.getElementById("control-language").addEventListener("change", (e) => {
    currentLang = e.target.value;
    stepTune.classList.add("active");
  });

  document.getElementById("control-style").addEventListener("change", (e) => {
    currentStyle = e.target.value;
    stepTune.classList.add("active");
  });

  // 5. Primary Lesson Plan Generation Action
  btnGenerate.addEventListener("click", async () => {
    btnGenerate.disabled = true;
    btnGenerate.innerHTML = `${render.getSpinnerSvg()} <span>Structuring lesson plan...</span>`;

    generationPanel.classList.add("show");
    const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    // Phase 1: Analyzing material (0 -> 40%)
    progressFill.style.width = "40%";
    stage1.classList.add("current");
    await delay(600);

    // Phase 2: Structuring lesson nodes (40 -> 80%)
    stage1.classList.remove("current");
    stage1.classList.add("done");
    stage2.classList.add("current");
    progressFill.style.width = "80%";
    await delay(700);

    // Phase 3: Ready (80 -> 100%)
    stage2.classList.remove("current");
    stage2.classList.add("done");
    stage3.classList.add("current");
    stage3.classList.add("done");
    progressFill.style.width = "100%";

    btnGenerate.innerHTML = `<span>✓ Ready! Entering classroom...</span>`;
    await delay(450);

    // Connect to real backend if available, with graceful fallback to mock mode
    let mode = "live";
    let sessionId = activeSessionId;
    let token = activeToken;

    try {
      if (!sessionId) {
        const session = await api.createSession();
        sessionId = session.session_id;
        token = session.token;
      }

      if (sessionId && !sessionId.startsWith("mock_")) {
        // If not a document upload session, submit topic and constraints
        if (!currentFile) {
          await api.submitTopic(sessionId, currentTopic || "Newton's Laws of Motion", {
            level: currentLevel,
            language: currentLang,
            time_budget_min: parseInt(currentBudget) || 15,
            style: currentStyle,
          }, token);
        }
        // Generate real lesson plan via PlannerAgent
        await api.generatePlan(sessionId, token);
        mode = "live";
      } else {
        mode = "mock";
      }
    } catch (e) {
      console.warn("Live backend plan generation failed, using mock mode:", e);
      mode = "mock";
    }

    const effectiveTopic = currentTopic || (currentFile ? currentFile.name.replace(/\.[^/.]+$/, "") : "Newton's Laws of Motion");
    const params = new URLSearchParams({
      mode: mode,
      session_id: sessionId || "",
      token: token || "",
      topic: effectiveTopic,
      level: currentLevel,
      lang: currentLang,
      budget: currentBudget,
      style: currentStyle,
    });

    window.location.href = `classroom.html?${params.toString()}`;
  });
});
