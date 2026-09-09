document.addEventListener('DOMContentLoaded', () => {
  // -------------------------------------------------------------------------
  // State & Configuration
  // -------------------------------------------------------------------------
  const state = {
    useLiveLLM: true,
    activeTab: 'tab-planner',
    fsmActiveState: 'UNDERSTAND',
    fsmSessionId: 'test_fsm_session_01'
  };

  // -------------------------------------------------------------------------
  // Elements
  // -------------------------------------------------------------------------
  const llmToggle = document.getElementById('llm-mode-toggle');
  const llmLabel = document.getElementById('llm-mode-label');
  const navTabs = document.querySelectorAll('.nav-tab');
  const tabPanels = document.querySelectorAll('.tab-panel');

  // -------------------------------------------------------------------------
  // Init Status Check
  // -------------------------------------------------------------------------
  async function checkServerStatus() {
    try {
      const res = await fetch('/api/test/status');
      if (res.ok) {
        const data = await res.json();
        if (!data.gemini_api_key_configured) {
          llmToggle.checked = false;
          state.useLiveLLM = false;
          llmLabel.textContent = 'SmartMock (No API Key)';
        }
      }
    } catch (err) {
      console.warn('Status check failed:', err);
    }
  }
  checkServerStatus();

  // -------------------------------------------------------------------------
  // Tab Switching
  // -------------------------------------------------------------------------
  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.getAttribute('data-tab');
      navTabs.forEach(t => t.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.add('active');
      state.activeTab = targetId;

      if (targetId === 'tab-logs') {
        loadRecentLogs();
      }
    });
  });

  // LLM Toggle
  llmToggle.addEventListener('change', (e) => {
    state.useLiveLLM = e.target.checked;
    llmLabel.textContent = state.useLiveLLM ? 'Live Gemini API' : 'SmartMock (Offline)';
  });

  // Helpers
  function setBtnLoading(btn, isLoading) {
    const text = btn.querySelector('.btn-text');
    const spinner = btn.querySelector('.btn-spinner');
    if (isLoading) {
      btn.disabled = true;
      if (spinner) spinner.classList.remove('hidden');
    } else {
      btn.disabled = false;
      if (spinner) spinner.classList.add('hidden');
    }
  }

  function renderJSON(container, data) {
    container.innerHTML = `<pre class="json-viewport">${JSON.stringify(data, null, 2)}</pre>`;
  }

  // -------------------------------------------------------------------------
  // 1. Planner Agent Execution
  // -------------------------------------------------------------------------
  const btnRunPlanner = document.getElementById('btn-run-planner');
  const plannerOutput = document.getElementById('planner-output');
  const plannerMeta = document.getElementById('planner-meta');

  btnRunPlanner.addEventListener('click', async () => {
    setBtnLoading(btnRunPlanner, true);
    plannerOutput.innerHTML = `<div class="empty-state"><span class="btn-spinner"></span><p>Planner Agent structuring curriculum DAG...</p></div>`;

    const payload = {
      topic: document.getElementById('planner-topic').value,
      level: document.getElementById('planner-level').value,
      language: document.getElementById('planner-lang').value,
      time_budget_min: document.getElementById('planner-budget').value,
      style: document.getElementById('planner-style').value,
      document_text: document.getElementById('planner-doc').value || null,
      use_live_llm: state.useLiveLLM
    };

    try {
      const res = await fetch('/api/test/planner', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail?.error || 'Planning failed');
      }

      const plan = data.plan;
      plannerMeta.innerHTML = `
        <span class="badge badge-accent">${data.duration_ms} ms</span>
        <span class="badge badge-success">${plan.nodes?.length || 0} Nodes</span>
      `;

      let nodesHtml = '<div class="dag-container">';
      plan.nodes.forEach((node, idx) => {
        const depthClass = node.depth === 'intro' ? 'badge-accent' : (node.depth === 'core' ? 'badge-success' : 'badge-purple');
        nodesHtml += `
          <div class="dag-node-card">
            <div class="dag-node-header">
              <span class="dag-node-title">Step ${idx + 1}: ${node.concept}</span>
              <div class="dag-node-badges">
                <span class="badge ${depthClass}">${node.depth}</span>
                <span class="badge">${node.est_minutes} min</span>
                <span class="badge badge-warning">${node.visual_type}</span>
                ${node.checkpoint_question ? '<span class="badge badge-success">❓ Checkpoint</span>' : ''}
              </div>
            </div>
            <p class="subtitle">Node ID: <code>${node.node_id}</code></p>
          </div>
        `;
      });
      nodesHtml += '</div>';

      nodesHtml += `
        <details style="margin-top: 16px;">
          <summary style="cursor: pointer; font-size: 12px; color: var(--text-secondary);">View Raw Contract §5 JSON</summary>
          <pre class="json-viewport" style="margin-top: 8px;">${JSON.stringify(plan, null, 2)}</pre>
        </details>
      `;

      plannerOutput.innerHTML = nodesHtml;
    } catch (err) {
      plannerOutput.innerHTML = `<div class="decision-box" style="background: var(--danger-bg);"><div class="decision-action" style="color: var(--danger);">ERROR</div><p class="decision-reason">${err.message}</p></div>`;
    } finally {
      setBtnLoading(btnRunPlanner, false);
    }
  });

  // -------------------------------------------------------------------------
  // 2. Explainer Agent Execution
  // -------------------------------------------------------------------------
  const btnRunExplainer = document.getElementById('btn-run-explainer');
  const explainerOutput = document.getElementById('explainer-output');
  const explainerMeta = document.getElementById('explainer-meta');

  btnRunExplainer.addEventListener('click', async () => {
    setBtnLoading(btnRunExplainer, true);
    explainerOutput.innerHTML = `<div class="empty-state"><span class="btn-spinner"></span><p>Explainer Agent crafting spoken script & visuals...</p></div>`;

    const chunksVal = document.getElementById('explainer-chunks').value.trim();
    const payload = {
      concept: document.getElementById('explainer-concept').value,
      depth: document.getElementById('explainer-depth').value,
      visual_type: document.getElementById('explainer-visual').value,
      previous_feedback: document.getElementById('explainer-feedback').value || null,
      grounding_chunks: chunksVal ? [chunksVal] : null,
      use_live_llm: state.useLiveLLM
    };

    try {
      const res = await fetch('/api/test/explainer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.error || 'Explanation failed');

      const seg = data.segment;
      const cueClass = seg.avatar_cue === 'emphasis' ? 'badge-warning' : (seg.avatar_cue === 'questioning' ? 'badge-purple' : 'badge-accent');

      explainerMeta.innerHTML = `
        <span class="badge badge-accent">${data.duration_ms} ms</span>
        <span class="badge ${cueClass}">Cue: ${seg.avatar_cue}</span>
      `;

      let html = `
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div class="dag-node-card" style="border-left-color: var(--accent-secondary);">
            <div class="dag-node-header">
              <span class="dag-node-title">🎙️ Spoken Teacher Script</span>
              <span class="badge badge-accent">${seg.script_text.split(' ').length} words</span>
            </div>
            <p style="font-size: 15px; line-height: 1.6; color: var(--text-primary);">${seg.script_text}</p>
          </div>

          <div class="dag-node-card" style="border-left-color: var(--purple);">
            <div class="dag-node-header">
              <span class="dag-node-title">🖼️ Visual Specification (${seg.visual_spec.type})</span>
            </div>
            <pre class="json-viewport">${typeof seg.visual_spec.content === 'object' ? JSON.stringify(seg.visual_spec.content, null, 2) : seg.visual_spec.content}</pre>
          </div>
        </div>
      `;

      explainerOutput.innerHTML = html;
    } catch (err) {
      explainerOutput.innerHTML = `<div class="decision-box" style="background: var(--danger-bg);"><div class="decision-action" style="color: var(--danger);">ERROR</div><p class="decision-reason">${err.message}</p></div>`;
    } finally {
      setBtnLoading(btnRunExplainer, false);
    }
  });

  // -------------------------------------------------------------------------
  // 3. Questioner Agent Execution
  // -------------------------------------------------------------------------
  const btnRunQuestioner = document.getElementById('btn-run-questioner');
  const questionerOutput = document.getElementById('questioner-output');
  const questionerMeta = document.getElementById('questioner-meta');

  btnRunQuestioner.addEventListener('click', async () => {
    setBtnLoading(btnRunQuestioner, true);
    questionerOutput.innerHTML = `<div class="empty-state"><span class="btn-spinner"></span><p>Synthesizing formative checkpoint question...</p></div>`;

    const payload = {
      concept: document.getElementById('questioner-concept').value,
      depth: document.getElementById('questioner-depth').value,
      visual_type: document.getElementById('questioner-visual').value,
      recent_script: document.getElementById('questioner-script').value || null,
      use_live_llm: state.useLiveLLM
    };

    try {
      const res = await fetch('/api/test/questioner', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.error || 'Question synthesis failed');

      const q = data.question;
      const typeClass = q.type === 'mcq' ? 'badge-accent' : (q.type === 'problem' ? 'badge-warning' : 'badge-purple');

      questionerMeta.innerHTML = `
        <span class="badge badge-accent">${data.duration_ms} ms</span>
        <span class="badge ${typeClass}">${q.type.toUpperCase()}</span>
      `;

      let optionsHtml = '';
      if (q.options && q.options.length > 0) {
        optionsHtml = '<div style="margin-top: 14px; display: flex; flex-direction: column; gap: 8px;">';
        q.options.forEach((opt, idx) => {
          optionsHtml += `
            <div style="padding: 10px 14px; background: rgba(255,255,255,0.05); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 10px;">
              <span class="badge">${String.fromCharCode(65 + idx)}</span>
              <span>${opt}</span>
            </div>
          `;
        });
        optionsHtml += '</div>';
      }

      let html = `
        <div class="dag-node-card" style="border-left-color: var(--accent-primary);">
          <div class="dag-node-header">
            <span class="dag-node-title">${q.question_text}</span>
          </div>
          ${optionsHtml}
          <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); font-size: 13px; color: var(--text-secondary);">
            <strong>Expected Concept Evaluated:</strong> <code>${q.expected_concept}</code>
          </div>
        </div>
      `;

      questionerOutput.innerHTML = html;
    } catch (err) {
      questionerOutput.innerHTML = `<div class="decision-box" style="background: var(--danger-bg);"><div class="decision-action" style="color: var(--danger);">ERROR</div><p class="decision-reason">${err.message}</p></div>`;
    } finally {
      setBtnLoading(btnRunQuestioner, false);
    }
  });

  // -------------------------------------------------------------------------
  // 4. Adaptation Controller Execution
  // -------------------------------------------------------------------------
  const btnRunAdaptation = document.getElementById('btn-run-adaptation');
  const adaptationOutput = document.getElementById('adaptation-output');
  const adaptationMeta = document.getElementById('adaptation-meta');

  btnRunAdaptation.addEventListener('click', async () => {
    setBtnLoading(btnRunAdaptation, true);

    const payload = {
      node_id: document.getElementById('adapt-node').value,
      correct: document.getElementById('adapt-correct').checked,
      partial_credit: parseFloat(document.getElementById('adapt-partial').value) || 0.0,
      confidence: parseFloat(document.getElementById('adapt-confidence').value) || 0.85,
      misconception_tag: document.getElementById('adapt-misconception').value || null,
      feedback_text: document.getElementById('adapt-feedback').value,
      consecutive_failures_on_node: parseInt(document.getElementById('adapt-failures').value) || 1
    };

    try {
      const res = await fetch('/api/test/adaptation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.error || 'Adaptation evaluation failed');

      const dec = data.decision;
      let actionBg = 'var(--success-bg)';
      let actionColor = 'var(--success)';

      if (dec.action === 'MODIFY') {
        actionBg = 'var(--warning-bg)';
        actionColor = 'var(--warning)';
      } else if (dec.action === 'REGENERATE') {
        actionBg = 'var(--purple-bg)';
        actionColor = 'var(--purple)';
      } else if (dec.action === 'HUMAN') {
        actionBg = 'var(--danger-bg)';
        actionColor = 'var(--danger)';
      }

      adaptationMeta.innerHTML = `<span class="badge badge-accent">${data.duration_ms} ms</span>`;

      adaptationOutput.innerHTML = `
        <div class="decision-box" style="background: ${actionBg};">
          <div class="decision-action" style="color: ${actionColor};">${dec.action}</div>
          <p class="decision-reason">${dec.reason}</p>
          <p style="margin-top: 10px; font-size: 12px; color: var(--text-muted);">Target Node: <code>${dec.target_node_id}</code></p>
        </div>
      `;
    } catch (err) {
      adaptationOutput.innerHTML = `<div class="decision-box" style="background: var(--danger-bg);"><div class="decision-action" style="color: var(--danger);">ERROR</div><p class="decision-reason">${err.message}</p></div>`;
    } finally {
      setBtnLoading(btnRunAdaptation, false);
    }
  });

  // -------------------------------------------------------------------------
  // 5. FSM Step Simulator
  // -------------------------------------------------------------------------
  const btnStepFSM = document.getElementById('btn-step-fsm');
  const btnResetFSM = document.getElementById('btn-reset-fsm');
  const fsmOutputDisplay = document.getElementById('fsm-output-display');
  const fsmStateSelect = document.getElementById('fsm-current-state');
  const fsmNodes = document.querySelectorAll('.fsm-node');

  function updateFSMRibbon(activeState) {
    fsmNodes.forEach(n => {
      if (n.getAttribute('data-state') === activeState) {
        n.classList.add('active');
      } else {
        n.classList.remove('active');
      }
    });
  }

  btnStepFSM.addEventListener('click', async () => {
    setBtnLoading(btnStepFSM, true);

    let parsedInputs = {};
    try {
      parsedInputs = JSON.parse(document.getElementById('fsm-inputs-json').value);
    } catch (err) {
      alert('Invalid JSON in inputs textarea');
      setBtnLoading(btnStepFSM, false);
      return;
    }

    const payload = {
      session_id: document.getElementById('fsm-session-id').value,
      current_state: fsmStateSelect.value,
      inputs: parsedInputs,
      use_live_llm: state.useLiveLLM
    };

    try {
      const res = await fetch('/api/test/fsm/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.error || 'FSM step failed');

      updateFSMRibbon(data.next_state);
      fsmStateSelect.value = data.next_state;

      fsmOutputDisplay.innerHTML = `<pre class="json-viewport">${JSON.stringify(data, null, 2)}</pre>`;
    } catch (err) {
      fsmOutputDisplay.innerHTML = `<div class="decision-box" style="background: var(--danger-bg);"><div class="decision-action" style="color: var(--danger);">ERROR</div><p class="decision-reason">${err.message}</p></div>`;
    } finally {
      setBtnLoading(btnStepFSM, false);
    }
  });

  btnResetFSM.addEventListener('click', () => {
    fsmStateSelect.value = 'UNDERSTAND';
    updateFSMRibbon('UNDERSTAND');
    document.getElementById('fsm-session-id').value = 'session_' + Math.floor(Math.random() * 10000);
    fsmOutputDisplay.innerHTML = `<p class="text-muted">Session reset. Ready for UNDERSTAND step.</p>`;
  });

  // -------------------------------------------------------------------------
  // 6. Log & Trace Explorer
  // -------------------------------------------------------------------------
  const logsTableBody = document.getElementById('logs-table-body');
  const logDetailContent = document.getElementById('log-detail-content');
  const logDetailId = document.getElementById('log-detail-id');
  const logsFilter = document.getElementById('logs-filter-category');
  const btnRefreshLogs = document.getElementById('btn-refresh-logs');

  async function loadRecentLogs() {
    logsTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Loading latest execution logs...</td></tr>`;
    const cat = logsFilter.value;
    const url = `/api/test/logs?limit=40${cat ? `&category=${cat}` : ''}`;

    try {
      const res = await fetch(url);
      const data = await res.json();

      if (!data || data.length === 0) {
        logsTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No test execution logs found yet. Run any test above to generate traces.</td></tr>`;
        return;
      }

      let rowsHtml = '';
      data.forEach(item => {
        const statusBadge = item.status === 'SUCCESS' || item.status === 'COMPLETED'
          ? '<span class="badge badge-success">OK</span>'
          : '<span class="badge badge-danger">ERROR</span>';

        const timeStr = item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : 'N/A';

        rowsHtml += `
          <tr data-cat="${item.category}" data-file="${item.filename}">
            <td>${statusBadge}</td>
            <td><span class="badge">${item.category}</span></td>
            <td><strong>${item.action}</strong></td>
            <td>${item.duration_ms} ms</td>
            <td>${timeStr}</td>
            <td><button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;">View</button></td>
          </tr>
        `;
      });

      logsTableBody.innerHTML = rowsHtml;

      // Row click listener
      logsTableBody.querySelectorAll('tr').forEach(row => {
        row.addEventListener('click', async () => {
          logsTableBody.querySelectorAll('tr').forEach(r => r.classList.remove('selected'));
          row.classList.add('selected');

          const cat = row.getAttribute('data-cat');
          const file = row.getAttribute('data-file');
          if (cat && file) {
            await loadLogDetail(cat, file);
          }
        });
      });
    } catch (err) {
      logsTableBody.innerHTML = `<tr><td colspan="6" class="text-center" style="color: var(--danger);">Failed to load logs: ${err.message}</td></tr>`;
    }
  }

  async function loadLogDetail(category, filename) {
    logDetailId.textContent = filename;
    logDetailContent.innerHTML = `<p class="text-muted">Loading trace manifest...</p>`;

    try {
      const res = await fetch(`/api/test/logs/${category}/${filename}`);
      const data = await res.json();
      logDetailContent.innerHTML = `<pre class="json-viewport">${JSON.stringify(data, null, 2)}</pre>`;
    } catch (err) {
      logDetailContent.innerHTML = `<p style="color: var(--danger);">Failed to retrieve log: ${err.message}</p>`;
    }
  }

  logsFilter.addEventListener('change', loadRecentLogs);
  btnRefreshLogs.addEventListener('click', loadRecentLogs);
});
