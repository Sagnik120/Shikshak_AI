/**
 * Shikshak AI — Avatar & Voice Isolated Web Testbed
 * Pure Vanilla JavaScript Client (Light Professional Theme)
 * Connects to Port 8004
 */

document.addEventListener("DOMContentLoaded", () => {
  // State
  let serverStatus = null;
  let currentLogData = null;

  // Preset templates for visual slides
  const visualPresets = {
    equation: {
      content: "\\begin{aligned} ax^2 + bx + c &= 0 \\\\ x^2 + \\frac{b}{a}x &= -\\frac{c}{a} \\\\ x &= \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a} \\end{aligned}",
      steps: "Step 1: Given general quadratic ax^2 + bx + c = 0\nStep 2: Divide by leading coefficient a\nStep 3: Complete the square by adding (b/2a)^2\nStep 4: Take square root and isolate x\nStep 5: Conclude x = (-b +- sqrt(b^2 - 4ac)) / 2a",
      showSteps: true,
      showOutput: false,
    },
    code: {
      content: "def binary_search(arr: list[int], target: int) -> int:\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1",
      steps: "Initialize pointers: low = 0, high = 5\nInspect midpoint: mid = 2, arr[2] = 5\n5 < target (7), eliminate left half: low = 3\nInspect midpoint: mid = 4, arr[4] = 9\n9 > target (7), eliminate right half: high = 3\nInspect midpoint: mid = 3, arr[3] = 7: Match found!",
      output: "Target 7 found at index 3. Search completed in 3 iterations (O(log n)).",
      showSteps: true,
      showOutput: true,
    },
    graph: {
      content: "f(x) = x^2 - 4*x + 3",
      steps: "Domain: [-1, 5]\nAxis of symmetry: x = 2\nVertex: (2, -1)\nRoots: x = 1 and x = 3",
      showSteps: true,
      showOutput: false,
    },
    diagram: {
      content: JSON.stringify({
        title: "Transformer Encoder Architecture",
        nodes: [
          { id: "input", label: "Input Tokens", type: "input" },
          { id: "emb", label: "Positional Embedding", type: "process" },
          { id: "mha", label: "Multi-Head Attention", type: "core" },
          { id: "ffn", label: "Feed Forward Network", type: "core" },
          { id: "output", label: "Contextual Vectors", type: "output" }
        ],
        edges: [
          { from: "input", to: "emb" },
          { from: "emb", to: "mha" },
          { from: "mha", to: "ffn" },
          { from: "ffn", to: "output" }
        ]
      }, null, 2),
      steps: "Input tokenization & embedding\nSelf-attention computation across all heads\nPointwise feed-forward transformations\nResidual addition and layer normalization",
      showSteps: true,
      showOutput: false,
    },
    timeline: {
      content: JSON.stringify({
        title: "Key Milestones in Machine Learning",
        events: [
          { year: "1958", title: "Perceptron", desc: "Frank Rosenblatt invents first artificial neural model." },
          { year: "1986", title: "Backpropagation", desc: "Rumelhart, Hinton & Williams popularize gradient descent." },
          { year: "2012", title: "AlexNet", desc: "Deep CNNs win ImageNet by a massive margin." },
          { year: "2017", title: "Attention Is All You Need", desc: "Vaswani et al. introduce Transformer architecture." },
          { year: "2024", title: "Multimodal AI Tutors", desc: "Autonomous avatar pedagogues democratize personalized education." }
        ]
      }, null, 2),
      steps: "1958: Single layer perceptron foundations\n1986: Multilayer error propagation\n2012: GPU-accelerated deep learning era\n2017: Attention-based sequence architectures\n2024: End-to-end multimodal teaching agents",
      showSteps: true,
      showOutput: false,
    },
    map: {
      content: JSON.stringify({
        title: "Ancient Trade Routes: Silk Road",
        center: { lat: 34.0, lng: 70.0 },
        landmarks: [
          { name: "Chang'an", role: "Eastern Terminus", lat: 34.3, lng: 108.9 },
          { name: "Dunhuang", role: "Oasis Crossroads", lat: 40.1, lng: 94.6 },
          { name: "Samarkand", role: "Central Trading Hub", lat: 39.6, lng: 66.9 },
          { name: "Antioch", role: "Mediterranean Port", lat: 36.2, lng: 36.1 }
        ]
      }, null, 2),
      steps: "Departure from Chang'an through Hexi Corridor\nCrossing Taklamakan desert via Dunhuang\nHigh-altitude pass into Samarkand bazaar\nArrival at Mediterranean ports",
      showSteps: true,
      showOutput: false,
    },
    image: {
      content: "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1344&auto=format&fit=crop&q=80",
      steps: "Microscope specimen slide\nIdentified cell nucleus and membrane structure",
      showSteps: true,
      showOutput: false,
    }
  };

  // ---------------------------------------------------------------------------
  // 1. System Health & Initial Load
  // ---------------------------------------------------------------------------
  async function checkServerStatus() {
    const statusDot = document.querySelector(".status-dot");
    const statusText = document.getElementById("status-text");

    try {
      const res = await fetch("/api/test/status");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      serverStatus = await res.json();

      statusDot.className = "status-dot ready";
      statusText.textContent = `Online • Port ${serverStatus.port} • PyTorch: ${serverStatus.avatar.device.toUpperCase()}`;
    } catch (err) {
      statusDot.className = "status-dot";
      statusDot.style.background = "var(--danger)";
      statusText.textContent = `Offline: ${err.message}`;
    }
  }

  // ---------------------------------------------------------------------------
  // 2. Navigation Tabs
  // ---------------------------------------------------------------------------
  const tabButtons = document.querySelectorAll(".nav-tab");
  const tabPanels = document.querySelectorAll(".tab-panel");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTabId = btn.getAttribute("data-tab");

      tabButtons.forEach(b => b.classList.remove("active"));
      tabPanels.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPanel = document.getElementById(targetTabId);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }

      if (targetTabId === "logs-tab") {
        loadLogs();
      }
    });
  });

  // ---------------------------------------------------------------------------
  // 3. Tab 1: TTS Studio
  // ---------------------------------------------------------------------------
  const btnSynthesizeTts = document.getElementById("btn-synthesize-tts");
  const ttsResultsBody = document.getElementById("tts-results-body");
  const ttsResultBadge = document.getElementById("tts-result-badge");

  btnSynthesizeTts?.addEventListener("click", async () => {
    const text = document.getElementById("tts-text").value.trim();
    const language = document.getElementById("tts-language").value;
    const provider = document.getElementById("tts-provider").value;
    const cue = document.getElementById("tts-cue").value;
    const customVoice = document.getElementById("tts-voice-id").value.trim() || undefined;

    if (!text) {
      alert("Please enter script text to narrate.");
      return;
    }

    btnSynthesizeTts.disabled = true;
    ttsResultBadge.textContent = "Synthesizing...";
    ttsResultBadge.className = "badge warning";

    ttsResultsBody.innerHTML = `
      <div class="empty-state">
        <div class="spinner"></div>
        <p style="margin-top: 1rem;">Synthesizing speech via <strong>${provider}</strong> engine...</p>
      </div>
    `;

    try {
      const res = await fetch("/api/test/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          language,
          provider,
          avatar_cue: cue,
          voice_id: customVoice,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail?.error || "TTS synthesis failed");
      }

      ttsResultBadge.textContent = "Success";
      ttsResultBadge.className = "badge success";

      // Render Audio Player + Metrics + Timestamps
      let timestampsHtml = "";
      if (data.timestamps && data.timestamps.length > 0) {
        timestampsHtml = `
          <div style="margin-top: 1.25rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
              <h4 style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">
                WebVTT Word-Level Alignment (${data.word_count} tokens)
              </h4>
              ${data.vtt_url ? `<a href="${data.vtt_url}" target="_blank" class="btn btn-secondary btn-sm">Download .vtt</a>` : ""}
            </div>
            <div style="max-height: 220px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
              <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; font-family: var(--font-mono);">
                <thead>
                  <tr style="background: var(--bg-tertiary); text-align: left; border-bottom: 1px solid var(--border-color);">
                    <th style="padding: 6px 12px;">Start</th>
                    <th style="padding: 6px 12px;">End</th>
                    <th style="padding: 6px 12px;">Word Token</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.timestamps.map(ts => `
                    <tr style="border-bottom: 1px solid var(--border-color);">
                      <td style="padding: 6px 12px; color: var(--primary);">${ts.start_sec.toFixed(3)}s</td>
                      <td style="padding: 6px 12px; color: var(--text-muted);">${ts.end_sec.toFixed(3)}s</td>
                      <td style="padding: 6px 12px; font-weight: 500;">${ts.word}</td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          </div>
        `;
      }

      ttsResultsBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="result-media-box">
            <audio controls autoplay style="width: 100%; border-radius: var(--radius-sm);" src="${data.audio_url}">
              Your browser does not support the audio element.
            </audio>
          </div>

          <div class="metrics-grid">
            <div class="metric-box">
              <span class="metric-label">Duration</span>
              <span class="metric-val">${data.duration_sec.toFixed(2)}s</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Sample Rate</span>
              <span class="metric-val">${data.sample_rate || 24000} Hz</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Word Count</span>
              <span class="metric-val">${data.word_count}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Log Trace</span>
              <span class="metric-val">
                <a href="#logs" class="view-log-link" data-category="tts" data-file="${data.log_file.split('/').pop()}">${data.log_id.slice(0, 8)}</a>
              </span>
            </div>
          </div>

          ${timestampsHtml}
        </div>
      `;

      bindLogLinks();
    } catch (err) {
      ttsResultBadge.textContent = "Error";
      ttsResultBadge.className = "badge danger";
      ttsResultsBody.innerHTML = `
        <div class="empty-state" style="color: var(--danger);">
          <p><strong>Speech Synthesis Failed:</strong> ${err.message}</p>
          <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;">Check the Structured Log Explorer for the full stack trace.</p>
        </div>
      `;
    } finally {
      btnSynthesizeTts.disabled = false;
    }
  });

  // ---------------------------------------------------------------------------
  // 4. Tab 2: Avatar Studio
  // ---------------------------------------------------------------------------
  const btnGenerateAvatar = document.getElementById("btn-generate-avatar");
  const avatarResultsBody = document.getElementById("avatar-results-body");
  const avatarResultBadge = document.getElementById("avatar-result-badge");

  btnGenerateAvatar?.addEventListener("click", async () => {
    const script_text = document.getElementById("avatar-script-text").value.trim();
    const engine = document.getElementById("avatar-engine").value;
    const cue = document.getElementById("avatar-cue-select").value;

    if (!script_text) {
      alert("Please enter script context.");
      return;
    }

    btnGenerateAvatar.disabled = true;
    avatarResultBadge.textContent = "Rendering...";
    avatarResultBadge.className = "badge warning";

    avatarResultsBody.innerHTML = `
      <div class="empty-state">
        <div class="spinner"></div>
        <p style="margin-top: 1rem;">Rendering avatar frames via <strong>${engine}</strong> engine...</p>
      </div>
    `;

    try {
      const res = await fetch("/api/test/avatar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          script_text,
          engine,
          avatar_cue: cue,
          language: "en",
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail?.error || "Avatar generation failed");
      }

      avatarResultBadge.textContent = "Success";
      avatarResultBadge.className = "badge success";

      let sampleFramesHtml = "";
      if (data.sample_frame_urls && data.sample_frame_urls.length > 0) {
        sampleFramesHtml = `
          <div style="margin-top: 1.25rem;">
            <h4 style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.5rem;">
              Extracted Keyframe Carousel (24 FPS Transparent Visemes)
            </h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 10px;">
              ${data.sample_frame_urls.map((url, i) => `
                <div style="border: 1px solid var(--border-color); border-radius: var(--radius-sm); overflow: hidden; background: #fafafa; text-align: center;">
                  <img src="${url}" alt="Viseme Frame ${i+1}" style="width: 100%; height: 95px; object-fit: contain; background: repeating-conic-gradient(#f0f0f0 0% 25%, #ffffff 0% 50%) 50% / 16px 16px;">
                  <div style="padding: 4px; font-size: 0.7rem; font-family: var(--font-mono); color: var(--text-muted);">Frame ${i * 4 + 1}</div>
                </div>
              `).join("")}
            </div>
          </div>
        `;
      }

      avatarResultsBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="metrics-grid">
            <div class="metric-box">
              <span class="metric-label">Engine Tier</span>
              <span class="metric-val" style="color: var(--primary);">${data.tier_used.toUpperCase()}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Frame Count</span>
              <span class="metric-val">${data.frame_count} @ ${data.fps} FPS</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Mouth States</span>
              <span class="metric-val">${data.mouth_states_detected.join(", ")}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Log Trace</span>
              <span class="metric-val">
                <a href="#logs" class="view-log-link" data-category="avatar" data-file="${data.log_file.split('/').pop()}">${data.log_id.slice(0, 8)}</a>
              </span>
            </div>
          </div>

          <div style="font-size: 0.85rem; padding: 10px 14px; background: var(--bg-tertiary); border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <strong>Tier Selection Reason:</strong> ${data.tier_used_reason}
          </div>

          ${sampleFramesHtml}
        </div>
      `;

      bindLogLinks();
    } catch (err) {
      avatarResultBadge.textContent = "Error";
      avatarResultBadge.className = "badge danger";
      avatarResultsBody.innerHTML = `
        <div class="empty-state" style="color: var(--danger);">
          <p><strong>Avatar Animation Failed:</strong> ${err.message}</p>
        </div>
      `;
    } finally {
      btnGenerateAvatar.disabled = false;
    }
  });

  // ---------------------------------------------------------------------------
  // 5. Tab 3: Visuals Studio
  // ---------------------------------------------------------------------------
  const visualTypeSelect = document.getElementById("visual-type-select");
  const visualContent = document.getElementById("visual-content");
  const visualSteps = document.getElementById("visual-steps");
  const groupVisualSteps = document.getElementById("group-visual-steps");
  const groupVisualOutput = document.getElementById("group-visual-output");
  const visualExecutionOutput = document.getElementById("visual-execution-output");
  const btnRenderVisual = document.getElementById("btn-render-visual");
  const visualsResultsBody = document.getElementById("visuals-results-body");
  const visualResultBadge = document.getElementById("visual-result-badge");

  function updateVisualPresets(type) {
    const preset = visualPresets[type] || visualPresets.equation;
    visualContent.value = preset.content;
    visualSteps.value = preset.steps || "";
    if (preset.output) {
      visualExecutionOutput.value = preset.output;
    } else {
      visualExecutionOutput.value = "";
    }

    groupVisualSteps.style.display = preset.showSteps ? "block" : "none";
    groupVisualOutput.style.display = preset.showOutput ? "block" : "none";
  }

  visualTypeSelect?.addEventListener("change", (e) => {
    updateVisualPresets(e.target.value);
  });

  // Initial preset
  if (visualTypeSelect) {
    updateVisualPresets(visualTypeSelect.value);
  }

  btnRenderVisual?.addEventListener("click", async () => {
    const visual_type = visualTypeSelect.value;
    const content = visualContent.value.trim();
    const stepsText = visualSteps.value.trim();
    const steps = stepsText ? stepsText.split("\n").map(s => s.trim()).filter(Boolean) : [];
    const execution_output = visualExecutionOutput.value.trim() || undefined;

    if (!content) {
      alert("Please enter visual slide content.");
      return;
    }

    btnRenderVisual.disabled = true;
    visualResultBadge.textContent = "Rendering...";
    visualResultBadge.className = "badge warning";

    visualsResultsBody.innerHTML = `
      <div class="empty-state">
        <div class="spinner"></div>
        <p style="margin-top: 1rem;">Rendering 1344 x 1080 slide for <strong>${visual_type}</strong>...</p>
      </div>
    `;

    try {
      const res = await fetch("/api/test/visuals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          visual_type,
          content,
          steps,
          execution_output,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail?.error || "Visual rendering failed");
      }

      visualResultBadge.textContent = "Success";
      visualResultBadge.className = "badge success";

      let stepsButtonsHtml = "";
      if (data.step_image_urls && data.step_image_urls.length > 0) {
        stepsButtonsHtml = `
          <div style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.5rem;">
            <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">
              Progressive Reveal Derivation Steps (${data.step_count} states)
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
              <button class="btn btn-secondary btn-sm active step-selector-btn" data-url="${data.primary_image_url}">Final Slide</button>
              ${data.step_image_urls.map((url, i) => `
                <button class="btn btn-secondary btn-sm step-selector-btn" data-url="${url}">Step ${i+1}</button>
              `).join("")}
            </div>
          </div>
        `;
      }

      visualsResultsBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="result-media-box" style="padding: 0; background: #0f172a; overflow: hidden; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <img id="active-visual-img" src="${data.primary_image_url}" alt="Rendered Slide" style="width: 100%; height: auto; display: block;">
          </div>

          <div class="metrics-grid">
            <div class="metric-box">
              <span class="metric-label">Subject Type</span>
              <span class="metric-val" style="color: var(--primary);">${data.visual_type.toUpperCase()}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Dimensions</span>
              <span class="metric-val">1344 x 1080</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Total Steps</span>
              <span class="metric-val">${data.step_count}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Log Trace</span>
              <span class="metric-val">
                <a href="#logs" class="view-log-link" data-category="visuals" data-file="${data.log_file.split('/').pop()}">${data.log_id.slice(0, 8)}</a>
              </span>
            </div>
          </div>

          ${stepsButtonsHtml}
        </div>
      `;

      // Step button interactive switcher
      const stepBtns = visualsResultsBody.querySelectorAll(".step-selector-btn");
      const activeImg = document.getElementById("active-visual-img");
      stepBtns.forEach(btn => {
        btn.addEventListener("click", () => {
          stepBtns.forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          const url = btn.getAttribute("data-url");
          if (activeImg && url) {
            activeImg.src = url;
          }
        });
      });

      bindLogLinks();
    } catch (err) {
      visualResultBadge.textContent = "Error";
      visualResultBadge.className = "badge danger";
      visualsResultsBody.innerHTML = `
        <div class="empty-state" style="color: var(--danger);">
          <p><strong>Visual Rendering Failed:</strong> ${err.message}</p>
        </div>
      `;
    } finally {
      btnRenderVisual.disabled = false;
    }
  });

  // ---------------------------------------------------------------------------
  // 6. Tab 4: Compositor Studio
  // ---------------------------------------------------------------------------
  const btnRenderFullVideo = document.getElementById("btn-render-full-video");
  const compResultsBody = document.getElementById("comp-results-body");
  const compResultBadge = document.getElementById("comp-result-badge");

  btnRenderFullVideo?.addEventListener("click", async () => {
    const node_id = document.getElementById("comp-node-id").value.trim() || "node_math_001";
    const script_text = document.getElementById("comp-script").value.trim();
    const language = document.getElementById("comp-language").value;
    const cue = document.getElementById("comp-cue").value;
    const tts_provider = document.getElementById("comp-tts-provider").value;
    const avatar_engine = document.getElementById("comp-avatar-engine").value;

    if (!script_text) {
      alert("Please enter narration script.");
      return;
    }

    btnRenderFullVideo.disabled = true;
    compResultBadge.textContent = "Compositing...";
    compResultBadge.className = "badge warning";

    compResultsBody.innerHTML = `
      <div class="empty-state">
        <div class="spinner"></div>
        <p style="margin-top: 1rem;">Compositing 1080p split-screen video via FFmpeg...</p>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem;">Synthesizing TTS $\\rightarrow$ Slide $\\rightarrow$ 24 FPS Visemes $\\rightarrow$ Video Stream</p>
      </div>
    `;

    try {
      const res = await fetch("/api/test/render_sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          node_id,
          script_text,
          language,
          avatar_cue: cue,
          tts_provider,
          avatar_engine,
          visual_spec: {
            type: "equation",
            content: "x^2 - 5x + 6 = (x - 2)(x - 3) = 0",
            steps: [
              "Step 1: Identify quadratic form ax^2 + bx + c = 0",
              "Step 2: Find two numbers that multiply to 6 and add to -5: -2 and -3",
              "Step 3: Factor expression: (x - 2)(x - 3) = 0",
              "Step 4: Solve roots: x = 2 or x = 3"
            ]
          }
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail?.error || "Video composition failed");
      }

      compResultBadge.textContent = "Success";
      compResultBadge.className = "badge success";

      compResultsBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="result-media-box" style="padding: 0; background: #000; border-radius: var(--radius-sm); overflow: hidden;">
            <video controls autoplay style="width: 100%; height: auto; display: block;" src="${data.video_url}">
              Your browser does not support the video tag.
            </video>
          </div>

          <div class="metrics-grid">
            <div class="metric-box">
              <span class="metric-label">Lesson Node</span>
              <span class="metric-val" style="font-size: 0.85rem; font-family: var(--font-mono);">${data.node_id}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Duration</span>
              <span class="metric-val">${data.duration_sec.toFixed(2)}s</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Resolution</span>
              <span class="metric-val">1920 x 1080</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Log Trace</span>
              <span class="metric-val">
                <a href="#logs" class="view-log-link" data-category="service" data-file="${data.log_file.split('/').pop()}">${data.log_id.slice(0, 8)}</a>
              </span>
            </div>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--bg-tertiary); border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <span style="font-size: 0.85rem;"><strong>Output Video:</strong> <code>${data.video_url}</code></span>
            ${data.captions_vtt_url ? `<a href="${data.captions_vtt_url}" target="_blank" class="btn btn-secondary btn-sm">Captions VTT</a>` : ""}
          </div>
        </div>
      `;

      bindLogLinks();
    } catch (err) {
      compResultBadge.textContent = "Error";
      compResultBadge.className = "badge danger";
      compResultsBody.innerHTML = `
        <div class="empty-state" style="color: var(--danger);">
          <p><strong>Composition Failed:</strong> ${err.message}</p>
        </div>
      `;
    } finally {
      btnRenderFullVideo.disabled = false;
    }
  });

  // ---------------------------------------------------------------------------
  // 7. Tab 5: Structured Log Explorer
  // ---------------------------------------------------------------------------
  const logCategoryFilter = document.getElementById("log-category-filter");
  const btnRefreshLogs = document.getElementById("btn-refresh-logs");
  const logListContainer = document.getElementById("log-list-container");
  const logCount = document.getElementById("log-count");
  const selectedLogTitle = document.getElementById("selected-log-title");
  const selectedLogBadge = document.getElementById("selected-log-badge");
  const selectedLogMeta = document.getElementById("selected-log-meta");
  const metaFile = document.getElementById("meta-file");
  const metaFunc = document.getElementById("meta-func");
  const metaTime = document.getElementById("meta-time");
  const logContentDisplay = document.getElementById("log-content-display");

  async function loadLogs(filterCategory = null, autoSelectFile = null) {
    const category = filterCategory !== null ? filterCategory : (logCategoryFilter?.value || "");
    let url = `/api/test/logs?limit=50`;
    if (category) {
      url += `&category=${encodeURIComponent(category)}`;
    }

    logListContainer.innerHTML = `<div class="empty-state"><div class="spinner"></div><p style="margin-top:0.5rem;">Loading logs...</p></div>`;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load logs");
      const data = await res.json();

      logCount.textContent = data.total_logs;

      if (!data.logs || data.logs.length === 0) {
        logListContainer.innerHTML = `<div class="empty-state">No logs recorded in this category yet.</div>`;
        return;
      }

      logListContainer.innerHTML = data.logs.map(log => {
        const isSuccess = log.status === "success" || !log.status;
        const statusBadgeClass = isSuccess ? "badge success" : "badge danger";
        return `
          <div class="log-item-card" data-category="${log.category}" data-filename="${log.filename}">
            <div class="log-item-top">
              <span class="badge ${log.category === 'errors' ? 'danger' : 'info'}">${log.category.toUpperCase()}</span>
              <span class="log-time">${new Date(log.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="log-op">${log.operation || log.filename}</div>
            <div class="log-item-bottom">
              <span class="log-file-crumb">${(log.source_file || "").split('/').pop()}</span>
              <span class="${statusBadgeClass}">${log.status || "OK"}</span>
            </div>
          </div>
        `;
      }).join("");

      // Bind click handlers to cards
      const cards = logListContainer.querySelectorAll(".log-item-card");
      cards.forEach(card => {
        card.addEventListener("click", () => {
          cards.forEach(c => c.classList.remove("active"));
          card.classList.add("active");
          const cat = card.getAttribute("data-category");
          const fn = card.getAttribute("data-filename");
          fetchLogDetail(cat, fn);
        });
      });

      // Auto-select if requested
      if (autoSelectFile) {
        const targetCard = Array.from(cards).find(c => c.getAttribute("data-filename") === autoSelectFile);
        if (targetCard) {
          targetCard.click();
          targetCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      } else if (cards.length > 0) {
        cards[0].click();
      }
    } catch (err) {
      logListContainer.innerHTML = `<div class="empty-state" style="color:var(--danger)">Error loading logs: ${err.message}</div>`;
    }
  }

  async function fetchLogDetail(category, filename) {
    selectedLogTitle.textContent = `Loading ${filename}...`;
    logContentDisplay.textContent = "Fetching log payload...";

    try {
      const res = await fetch(`/api/test/logs/${category}/${filename}`);
      if (!res.ok) throw new Error(`Log not found (HTTP ${res.status})`);
      const logData = await res.json();
      currentLogData = logData;

      selectedLogTitle.textContent = `${logData.operation || logData.log_id || filename}`;
      selectedLogBadge.style.display = "inline-block";
      selectedLogBadge.textContent = logData.status ? logData.status.toUpperCase() : "SUCCESS";
      selectedLogBadge.className = (logData.status === "error" || logData.error) ? "badge danger" : "badge success";

      selectedLogMeta.style.display = "grid";
      metaFile.textContent = logData.source_file || "modules/avatar_voice/...";
      metaFunc.textContent = logData.source_function || "execute";
      metaTime.textContent = new Date(logData.timestamp).toLocaleString();

      logContentDisplay.textContent = JSON.stringify(logData, null, 2);
    } catch (err) {
      selectedLogTitle.textContent = "Log Read Error";
      selectedLogBadge.style.display = "none";
      selectedLogMeta.style.display = "none";
      logContentDisplay.textContent = `Failed to fetch log details: ${err.message}`;
    }
  }

  logCategoryFilter?.addEventListener("change", () => loadLogs());
  btnRefreshLogs?.addEventListener("click", () => loadLogs());

  function bindLogLinks() {
    document.querySelectorAll(".view-log-link").forEach(link => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const cat = link.getAttribute("data-category");
        const file = link.getAttribute("data-file");

        // Switch to logs tab
        const logsTabBtn = document.getElementById("tab-btn-logs");
        if (logsTabBtn) {
          logsTabBtn.click();
          if (logCategoryFilter) {
            logCategoryFilter.value = cat;
          }
          loadLogs(cat, file);
        }
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Initialize
  // ---------------------------------------------------------------------------
  checkServerStatus();
});
