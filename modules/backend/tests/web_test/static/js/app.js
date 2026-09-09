/**
 * Shikshak AI — Backend Module Testbed Client JS
 * Interacts with Port 8005 endpoints and logs traces.
 */

let activeSessionId = "";
let activeToken = "";
let activeWebSocket = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  checkServerStatus();
  bindEvents();
});

// -----------------------------------------------------------------------------
// Status & Health Check
// -----------------------------------------------------------------------------

async function checkServerStatus() {
  const statusText = document.getElementById("backend-status-text");
  try {
    const res = await fetch("/api/test/status");
    if (res.ok) {
      const data = await res.json();
      statusText.textContent = `FastAPI Ready (Sessions: ${data.active_sessions_count || 0})`;
    } else {
      statusText.textContent = "Status Check Failed";
    }
  } catch (err) {
    statusText.textContent = "Testbed Offline (Check Port 8005)";
  }
}

// -----------------------------------------------------------------------------
// Tab Switching
// -----------------------------------------------------------------------------

function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      tabPanels.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.classList.add("active");
        if (targetId === "tab-logs") {
          loadRecentLogs();
        }
      }
    });
  });
}

// -----------------------------------------------------------------------------
// Preset Helper
// -----------------------------------------------------------------------------

function setTopicPreset(topic, level, lang, timeBudget) {
  document.getElementById("input-topic-title").value = topic;
  document.getElementById("select-learner-level").value = level;
  document.getElementById("select-language").value = lang;
  document.getElementById("input-time-budget").value = timeBudget;
}

// -----------------------------------------------------------------------------
// Event Bindings
// -----------------------------------------------------------------------------

function bindEvents() {
  // Session Creation
  document.getElementById("btn-create-session").addEventListener("click", createSession);

  // Topic Submission
  document.getElementById("btn-submit-topic").addEventListener("click", submitTopic);

  // Document Upload
  document.getElementById("btn-simulate-upload").addEventListener("click", uploadDocument);

  // Lesson Plan
  document.getElementById("btn-generate-plan").addEventListener("click", generatePlan);

  // Learner Profile
  document.getElementById("btn-get-learner-profile").addEventListener("click", fetchLearnerProfile);

  // WebSocket Controls
  document.getElementById("btn-ws-connect").addEventListener("click", connectWebSocket);
  document.getElementById("btn-ws-disconnect").addEventListener("click", disconnectWebSocket);
  document.getElementById("btn-ws-step").addEventListener("click", () => sendWSMessage({ action: "step" }));
  document.getElementById("btn-ws-answer-correct").addEventListener("click", () => sendWSMessage({ action: "answer", answer: "Conservation of Energy" }));
  document.getElementById("btn-ws-answer-wrong").addEventListener("click", () => sendWSMessage({ action: "answer", answer: "Energy vanishes due to friction" }));
  document.getElementById("btn-ws-send-custom").addEventListener("click", sendCustomWSMessage);
  document.getElementById("btn-clear-ws-feed").addEventListener("click", clearWSTerminal);

  // Log Explorer
  document.getElementById("btn-refresh-logs").addEventListener("click", loadRecentLogs);
  document.getElementById("select-log-category").addEventListener("change", loadRecentLogs);
}

// -----------------------------------------------------------------------------
// REST API Handlers
// -----------------------------------------------------------------------------

async function createSession() {
  const jsonBox = document.getElementById("json-session-output");
  const latencyBadge = document.getElementById("session-latency-badge");
  const sessionInput = document.getElementById("input-active-session-id");
  const tokenInput = document.getElementById("input-active-session-token");
  const uploadSessionInput = document.getElementById("input-upload-session-id");
  const planSessionInput = document.getElementById("input-plan-session-id");

  const t0 = performance.now();
  jsonBox.textContent = "Creating session...";

  try {
    const res = await fetch("/api/test/sessions", { method: "POST" });
    const latency = Math.round(performance.now() - t0);
    latencyBadge.textContent = `Latency: ${latency} ms`;

    if (res.ok) {
      const data = await res.json();
      activeSessionId = data.session_id;
      activeToken = data.token;

      sessionInput.value = activeSessionId;
      tokenInput.value = activeToken;
      uploadSessionInput.value = activeSessionId;
      planSessionInput.value = activeSessionId;

      jsonBox.textContent = JSON.stringify(data, null, 2);
    } else {
      const err = await res.json();
      jsonBox.textContent = JSON.stringify(err, null, 2);
    }
  } catch (err) {
    jsonBox.textContent = `Error: ${err.message}`;
  }
}

async function submitTopic() {
  const jsonBox = document.getElementById("json-session-output");
  const latencyBadge = document.getElementById("session-latency-badge");

  if (!activeSessionId) {
    alert("Please generate or enter an active Session ID first.");
    return;
  }

  const topic = document.getElementById("input-topic-title").value;
  const level = document.getElementById("select-learner-level").value;
  const language = document.getElementById("select-language").value;
  const timeBudget = parseInt(document.getElementById("input-time-budget").value, 10);

  const t0 = performance.now();
  jsonBox.textContent = "Submitting topic...";

  try {
    const res = await fetch("/api/test/topic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: activeSessionId,
        topic: topic,
        level: level,
        language: language,
        time_budget_min: timeBudget,
      }),
    });
    const latency = Math.round(performance.now() - t0);
    latencyBadge.textContent = `Latency: ${latency} ms`;

    const data = await res.json();
    jsonBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    jsonBox.textContent = `Error: ${err.message}`;
  }
}

async function uploadDocument() {
  const jsonBox = document.getElementById("json-upload-output");
  const latencyBadge = document.getElementById("upload-latency-badge");
  const sessionId = document.getElementById("input-upload-session-id").value || activeSessionId;

  if (!sessionId) {
    alert("Please provide an active Session ID.");
    return;
  }

  const sampleText = document.getElementById("textarea-upload-sample").value;
  const blob = new Blob([sampleText], { type: "text/plain" });
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("file", blob, "physics_laws.txt");
  formData.append("level", "beginner");
  formData.append("language", "en");
  formData.append("time_budget_min", "15");

  const t0 = performance.now();
  jsonBox.textContent = "Uploading and parsing document via RAG...";

  try {
    const res = await fetch("/api/test/upload", {
      method: "POST",
      body: formData,
    });
    const latency = Math.round(performance.now() - t0);
    latencyBadge.textContent = `Latency: ${latency} ms`;

    const data = await res.json();
    jsonBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    jsonBox.textContent = `Error: ${err.message}`;
  }
}

async function generatePlan() {
  const jsonBox = document.getElementById("json-plan-output");
  const latencyBadge = document.getElementById("plan-latency-badge");
  const sessionId = document.getElementById("input-plan-session-id").value || activeSessionId;

  if (!sessionId) {
    alert("Please provide an active Session ID.");
    return;
  }

  const t0 = performance.now();
  jsonBox.textContent = "Running SessionDriver planner transition...";

  try {
    const res = await fetch("/api/test/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
    const latency = Math.round(performance.now() - t0);
    latencyBadge.textContent = `Latency: ${latency} ms`;

    const data = await res.json();
    jsonBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    jsonBox.textContent = `Error: ${err.message}`;
  }
}

async function fetchLearnerProfile() {
  const jsonBox = document.getElementById("json-plan-output");
  const learnerId = document.getElementById("input-learner-id").value || "learner_default_01";

  jsonBox.textContent = "Fetching learner profile...";
  try {
    const res = await fetch(`/api/test/learners/${learnerId}/profile`);
    const data = await res.json();
    jsonBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    jsonBox.textContent = `Error: ${err.message}`;
  }
}

// -----------------------------------------------------------------------------
// Live WebSocket Relay Handlers
// -----------------------------------------------------------------------------

function connectWebSocket() {
  const sessionId = activeSessionId || document.getElementById("input-active-session-id").value;
  if (!sessionId) {
    alert("Please create a session first before connecting WebSocket.");
    return;
  }

  const badge = document.getElementById("ws-status-badge");
  const connectBtn = document.getElementById("btn-ws-connect");
  const disconnectBtn = document.getElementById("btn-ws-disconnect");
  const actionBtns = [
    document.getElementById("btn-ws-step"),
    document.getElementById("btn-ws-answer-correct"),
    document.getElementById("btn-ws-answer-wrong"),
    document.getElementById("btn-ws-send-custom"),
  ];

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/api/test/ws/${sessionId}?token=${activeToken}`;

  appendWSTerminal("SYSTEM", `Connecting to ${wsUrl}...`);
  badge.textContent = "Connecting...";
  badge.className = "badge badge-amber";

  try {
    activeWebSocket = new WebSocket(wsUrl);

    activeWebSocket.onopen = () => {
      badge.textContent = "Connected (Live Relay)";
      badge.className = "badge badge-green";
      connectBtn.disabled = true;
      disconnectBtn.disabled = false;
      actionBtns.forEach((b) => (b.disabled = false));
      appendWSTerminal("SYSTEM", "WebSocket connected successfully! Live state relay active.");
    };

    activeWebSocket.onmessage = (event) => {
      try {
        const frame = JSON.parse(event.data);
        appendWSTerminal(`SERVER [${frame.event_type || "frame"}]`, JSON.stringify(frame.payload || frame, null, 2), "outbound");
      } catch (err) {
        appendWSTerminal("SERVER [RAW]", event.data, "outbound");
      }
    };

    activeWebSocket.onerror = (err) => {
      appendWSTerminal("ERROR", "WebSocket connection error.");
    };

    activeWebSocket.onclose = () => {
      badge.textContent = "Disconnected";
      badge.className = "badge badge-gray";
      connectBtn.disabled = false;
      disconnectBtn.disabled = true;
      actionBtns.forEach((b) => (b.disabled = true));
      appendWSTerminal("SYSTEM", "WebSocket disconnected.");
      activeWebSocket = null;
    };
  } catch (err) {
    appendWSTerminal("ERROR", `Failed to initialize WebSocket: ${err.message}`);
  }
}

function disconnectWebSocket() {
  if (activeWebSocket) {
    activeWebSocket.close();
  }
}

function sendWSMessage(payload) {
  if (!activeWebSocket || activeWebSocket.readyState !== WebSocket.OPEN) {
    alert("WebSocket is not connected.");
    return;
  }
  const raw = JSON.stringify(payload);
  activeWebSocket.send(raw);
  appendWSTerminal(`CLIENT [${payload.action || "message"}]`, raw, "inbound");
}

function sendCustomWSMessage() {
  const textarea = document.getElementById("textarea-ws-custom");
  try {
    const payload = JSON.parse(textarea.value);
    sendWSMessage(payload);
  } catch (err) {
    alert(`Invalid JSON format: ${err.message}`);
  }
}

function appendWSTerminal(sender, message, direction = "system") {
  const terminal = document.getElementById("ws-terminal");
  const item = document.createElement("div");
  item.className = `ws-message-item ${direction === "inbound" ? "ws-inbound" : (direction === "outbound" ? "ws-outbound" : "")}`;

  const time = new Date().toLocaleTimeString();
  item.innerHTML = `
    <div class="ws-header">
      <span>${sender}</span>
      <span>${time}</span>
    </div>
    <div style="white-space: pre-wrap; font-size: 0.8rem;">${message}</div>
  `;
  terminal.appendChild(item);
  terminal.scrollTop = terminal.scrollHeight;
}

function clearWSTerminal() {
  document.getElementById("ws-terminal").innerHTML = "";
}

// -----------------------------------------------------------------------------
// Log Explorer Handlers
// -----------------------------------------------------------------------------

async function loadRecentLogs() {
  const tbody = document.getElementById("log-table-body");
  const category = document.getElementById("select-log-category").value;

  tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 16px;">Loading logs...</td></tr>`;

  try {
    const url = category ? `/api/test/logs?category=${category}&limit=50` : `/api/test/logs?limit=50`;
    const res = await fetch(url);
    const logs = await res.json();

    if (!logs || logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">No test logs found in this category.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    logs.forEach((log) => {
      const tr = document.createElement("tr");
      const srcFile = (log.source && log.source.file) ? log.source.file.split("/").pop() : "-";
      const srcFn = (log.source && log.source.function) ? log.source.function : "-";
      const dateStr = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "-";

      tr.innerHTML = `
        <td style="font-family: var(--font-mono); font-size: 0.75rem;">${dateStr}</td>
        <td><span class="badge badge-gray">${log.category}</span></td>
        <td style="font-weight: 600;">${log.operation || "-"}</td>
        <td style="font-family: var(--font-mono); font-size: 0.75rem;">${srcFile} &rarr; ${srcFn}()</td>
        <td><span class="badge ${log.status === 'failed' ? 'badge-amber' : 'badge-green'}">${log.status || 'ok'}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="viewLogDetail('${log.category}', '${log.log_file.split('/').pop()}')">View Log</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--accent-error); padding: 16px;">Failed to load logs: ${err.message}</td></tr>`;
  }
}

async function viewLogDetail(category, filename) {
  const viewer = document.getElementById("log-viewer-content");
  const badge = document.getElementById("active-log-badge");

  badge.textContent = `${category}/${filename}`;
  viewer.textContent = "Loading trace contents...";

  try {
    const res = await fetch(`/api/test/logs/${category}/${filename}`);
    if (res.ok) {
      const data = await res.json();
      viewer.textContent = data.content;
    } else {
      viewer.textContent = "Failed to load log file content.";
    }
  } catch (err) {
    viewer.textContent = `Error reading log: ${err.message}`;
  }
}
