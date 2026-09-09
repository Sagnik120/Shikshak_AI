/**
 * Shikshak AI — ML Core Isolated Web Testbed
 * Pure Vanilla JavaScript Client (Light Professional Theme)
 * Connects to Port 8003
 */

document.addEventListener("DOMContentLoaded", () => {
  // State
  let serverStatus = null;
  let currentLogData = null;

  // Preset Configurations
  const evalPresets = {
    physics_ohm_correct: {
      node_id: "node_phys_ohm_001",
      response_type: "freeform",
      raw_answer: "Current increases linearly when voltage increases across a conductor if the temperature stays constant.",
      expected: "Current is directly proportional to voltage across a conductor provided temperature remains constant (V = IR).",
      grounding: "Ohm's law states that the electric current through a conductor between two points is directly proportional to the voltage across the two points under constant temperature conditions.",
      subject: "physics",
    },
    physics_ohm_partial: {
      node_id: "node_phys_ohm_002",
      response_type: "freeform",
      raw_answer: "Current is proportional to voltage in any electrical circuit.",
      expected: "Current is directly proportional to voltage across an ohmic conductor provided temperature remains constant.",
      grounding: "Ohm's law applies strictly to ohmic conductors under constant temperature.",
      subject: "physics",
    },
    physics_ohm_incorrect: {
      node_id: "node_phys_ohm_003",
      response_type: "freeform",
      raw_answer: "Voltage gets consumed by electrons as they flow through the wire, so current disappears.",
      expected: "Current is conserved across a circuit; voltage represents potential difference, not a consumable fluid.",
      grounding: "Electric charge is conserved. Potential difference provides energy to charges.",
      subject: "physics",
    },
    math_derivative_mcq: {
      node_id: "node_math_calc_001",
      response_type: "mcq",
      raw_answer: "B",
      expected: "B",
      grounding: "Question: What is the derivative of x^3? Option A: 3x. Option B: 3x^2. Option C: x^2/3.",
      subject: "math",
    },
    cs_recursion_freeform: {
      node_id: "node_cs_algo_001",
      response_type: "freeform",
      raw_answer: "The base case is a stopping condition that prevents the function from calling itself infinitely and blowing the call stack.",
      expected: "A terminating condition that halts further recursive calls and returns an explicit value without self-invocation.",
      grounding: "Every valid recursive function must contain at least one base case that terminates execution.",
      subject: "cs",
    },
  };

  const miscPresets = {
    gravity_fall: {
      subject: "physics",
      expected: "All objects in free fall experience equal gravitational acceleration g = 9.8 m/s^2 regardless of mass.",
      raw_answer: "A boulder falls much faster than a small pebble because the earth pulls heavier objects with much more gravitational force.",
    },
    current_consumed: {
      subject: "physics",
      expected: "Current is conserved in a single-loop series circuit; charge cannot accumulate or vanish.",
      raw_answer: "The first lightbulb consumes most of the current, so less electric current reaches the second lightbulb.",
    },
    negative_squaring: {
      subject: "math",
      expected: "Squaring any real negative number (-x)^2 always yields a positive real number.",
      raw_answer: "-4 squared is -16 because a negative sign always stays negative when multiplied.",
    },
    loop_off_by_one: {
      subject: "cs",
      expected: "An array of size N in zero-indexed languages has valid indices from 0 to N-1.",
      raw_answer: "Since the array has 10 elements, the loop must check indices from 1 to 10 inclusive.",
    },
  };

  const conceptsPresets = {
    quantum_mechanics: {
      text: "Quantum mechanics is a fundamental theory in physics that provides a description of the physical properties of nature at the scale of atoms and subatomic particles.\n---\nWave-particle duality posits that all matter exhibits both particle and wave behaviors. Light behaves as discrete packets of energy called photons.\n---\nSchrodinger's equation describes how the quantum state of a physical system changes with time via probability wavefunctions.",
      top_k: 8,
    },
    binary_search: {
      text: "Binary search is an efficient divide and conquer algorithm for finding an item from a sorted list of items.\n---\nIt works by repeatedly dividing in half the portion of the list that could contain the target key until you've narrowed the possible locations to just one.\n---\nThe time complexity of binary search is O(log n), where n is the number of elements in the sorted array.",
      top_k: 8,
    },
    organic_chemistry: {
      text: "Organic chemistry is a branch of chemistry that studies the structure, properties and reactions of organic compounds, which contain carbon in covalent bonding.\n---\nHydrocarbons are organic molecules consisting entirely of hydrogen and carbon. Alkanes have single bonds, while alkenes contain double carbon bonds.\n---\nFunctional groups such as hydroxyl, carboxyl, and amino groups dictate the chemical reactivity and biological properties of molecules.",
      top_k: 8,
    },
  };

  const visualsPresets = {
    math_quadratic: {
      subject: "mathematics",
      concept: "quadratic formula derivation",
    },
    physics_trajectory: {
      subject: "physics",
      concept: "projectile motion parabolic trajectory",
    },
    cs_binary_search: {
      subject: "computer science",
      concept: "binary search algorithm implementation",
    },
    history_silk_road: {
      subject: "history",
      concept: "ancient silk road trade routes",
    },
    biology_cell: {
      subject: "biology",
      concept: "eukaryotic cell organelle structure",
    },
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
      statusText.textContent = `Online • Port ${serverStatus.port} • Adapter: ${serverStatus.llm_adapter}`;
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
  // 3. Tab 1: Answer Evaluation Studio
  // ---------------------------------------------------------------------------
  const evalPresetSelect = document.getElementById("eval-preset-select");
  const evalNodeId = document.getElementById("eval-node-id");
  const evalResponseType = document.getElementById("eval-response-type");
  const evalExpectedConcept = document.getElementById("eval-expected-concept");
  const evalRawAnswer = document.getElementById("eval-raw-answer");
  const evalGroundingText = document.getElementById("eval-grounding-text");
  const evalSubject = document.getElementById("eval-subject");
  const btnRunEvaluation = document.getElementById("btn-run-evaluation");
  const evalResultsBody = document.getElementById("eval-results-body");
  const evalResultBadge = document.getElementById("eval-result-badge");

  evalPresetSelect?.addEventListener("change", (e) => {
    const preset = evalPresets[e.target.value];
    if (preset) {
      evalNodeId.value = preset.node_id;
      evalResponseType.value = preset.response_type;
      evalRawAnswer.value = preset.raw_answer;
      evalExpectedConcept.value = preset.expected;
      evalGroundingText.value = preset.grounding;
      evalSubject.value = preset.subject;
    }
  });

  btnRunEvaluation?.addEventListener("click", async () => {
    const node_id = evalNodeId.value.trim() || "node_001";
    const response_type = evalResponseType.value;
    const raw_answer = evalRawAnswer.value.trim();
    const expected_concept = evalExpectedConcept.value.trim();
    const grounding_text = evalGroundingText.value.trim() || undefined;
    const subject = evalSubject.value;

    if (!raw_answer || !expected_concept) {
      alert("Please provide both student raw answer and expected concept.");
      return;
    }

    btnRunEvaluation.disabled = true;
    evalResultBadge.textContent = "Evaluating...";
    evalResultBadge.className = "badge warning";

    evalResultsBody.innerHTML = `
      <div class="empty-state">
        <div class="spinner"></div>
        <p style="margin-top: 1rem;">Evaluating response via <strong>${response_type.toUpperCase()}</strong> pipeline...</p>
      </div>
    `;

    try {
      const res = await fetch("/api/test/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          node_id,
          response_type,
          raw_answer,
          expected_concept,
          grounding_text,
          subject,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.error || "Evaluation failed");

      const isCorrect = data.correct;
      evalResultBadge.textContent = isCorrect ? "CORRECT" : (data.partial_credit > 0 ? "PARTIAL" : "INCORRECT");
      evalResultBadge.className = isCorrect ? "badge success" : (data.partial_credit > 0 ? "badge warning" : "badge danger");

      let miscTagHtml = "";
      if (data.misconception_tag) {
        miscTagHtml = `
          <div style="margin-top: 1rem; padding: 12px 14px; background: var(--warning-light); border: 1px solid var(--warning-border); border-radius: var(--radius-sm);">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--warning); text-transform: uppercase;">Diagnosed Conceptual Trap</div>
            <div style="font-weight: 600; font-size: 0.95rem; margin-top: 2px;">${data.misconception_tag}</div>
          </div>
        `;
      }

      evalResultsBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="metrics-grid">
            <div class="metric-box">
              <span class="metric-label">Correctness</span>
              <span class="metric-val" style="color: ${isCorrect ? 'var(--success)' : 'var(--danger)'};">${isCorrect ? 'TRUE' : 'FALSE'}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Partial Credit</span>
              <span class="metric-val">${(data.partial_credit * 100).toFixed(0)}%</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Confidence</span>
              <span class="metric-val">${(data.confidence * 100).toFixed(1)}%</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Log Trace</span>
              <span class="metric-val">
                <a href="#logs" class="view-log-link" data-category="evaluation" data-file="${data.log_file.split('/').pop()}">${data.log_id.slice(0, 8)}</a>
              </span>
            </div>
          </div>

          <div style="padding: 12px 14px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Evaluation Tier Route</div>
            <div style="font-weight: 600; font-size: 0.9rem; margin-top: 2px;">${data.evaluation_tier}</div>
          </div>

          <div style="padding: 12px 14px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">Pedagogical Feedback</div>
            <p style="font-size: 0.9rem; color: var(--text-primary);">${data.feedback_text}</p>
          </div>

          ${miscTagHtml}
        </div>
      `;

      bindLogLinks();
    } catch (err) {
      evalResultBadge.textContent = "Error";
      evalResultBadge.className = "badge danger";
      evalResultsBody.innerHTML = `
        <div class="empty-state" style="color: var(--danger);">
          <p><strong>Evaluation Failed:</strong> ${err.message}</p>
        </div>
      `;
    } finally {
      btnRunEvaluation.disabled = false;
    }
  });

  // ---------------------------------------------------------------------------
  // 4. Tab 2: Misconception Classifier Studio
  // ---------------------------------------------------------------------------
  const miscPresetSelect = document.getElementById("misc-preset-select");
  const miscSubject = document.getElementById("misc-subject");
  const miscExpectedConcept = document.getElementById("misc-expected-concept");
  const miscRawAnswer = document.getElementById("misc-raw-answer");
  const btnDiagnoseMisconception = document.getElementById("btn-diagnose-misconception");
  const miscResultsBody = document.getElementById("misc-results-body");
  const miscResultBadge = document.getElementById("misc-result-badge");

  miscPresetSelect?.addEventListener("change", (e) => {
    const preset = miscPresets[e.target.value];
    if (preset) {
      miscSubject.value = preset.subject;
      miscExpectedConcept.value = preset.expected;
      miscRawAnswer.value = preset.raw_answer;
    }
  });

  btnDiagnoseMisconception?.addEventListener("click", async () => {
    const subject = miscSubject.value;
    const expected_concept = miscExpectedConcept.value.trim();
    const raw_answer = miscRawAnswer.value.trim();

    if (!raw_answer || !expected_concept) {
      alert("Please provide expected concept and student incorrect answer.");
      return;
    }

    btnDiagnoseMisconception.disabled = true;
    miscResultBadge.textContent = "Diagnosing...";
    miscResultBadge.className = "badge warning";

    miscResultsBody.innerHTML = `
      <div class="empty-state">
        <div class="spinner"></div>
        <p style="margin-top: 1rem;">Classifying error against <strong>${subject.toUpperCase()}</strong> taxonomy...</p>
      </div>
    `;

    try {
      const res = await fetch("/api/test/misconception", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject,
          expected_concept,
          raw_answer,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.error || "Misconception classification failed");

      if (data.diagnosed_tag) {
        miscResultBadge.textContent = "Diagnosed";
        miscResultBadge.className = "badge warning";
      } else {
        miscResultBadge.textContent = "No Taxonomy Match";
        miscResultBadge.className = "badge info";
      }

      miscResultsBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="metrics-grid">
            <div class="metric-box">
              <span class="metric-label">Taxonomy Domain</span>
              <span class="metric-val" style="color: var(--primary); text-transform: uppercase;">${data.subject}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Checked Tags</span>
              <span class="metric-val">${data.taxonomy_entries_checked} entries</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Diagnosis</span>
              <span class="metric-val">${data.diagnosed_tag ? "MATCH" : "NONE"}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Log Trace</span>
              <span class="metric-val">
                <a href="#logs" class="view-log-link" data-category="misconception" data-file="${data.log_file.split('/').pop()}">${data.log_id.slice(0, 8)}</a>
              </span>
            </div>
          </div>

          <div style="padding: 14px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Classified Misconception Tag</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: ${data.diagnosed_tag ? 'var(--warning)' : 'var(--text-secondary)'}; margin-top: 4px;">
              ${data.diagnosed_tag || "No standard misconception tag matched (generic conceptual gap)"}
            </div>
          </div>

          ${data.tag_description ? `
            <div style="padding: 12px 14px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">Pedagogical Description</div>
              <p style="font-size: 0.9rem; color: var(--text-primary);">${data.tag_description}</p>
            </div>
          ` : ""}

          ${data.remediation_hint ? `
            <div style="padding: 12px 14px; background: var(--primary-light); border: 1px solid #bfdbfe; border-radius: var(--radius-sm);">
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--primary); text-transform: uppercase; margin-bottom: 4px;">Remedial Teaching Action</div>
              <p style="font-size: 0.9rem; color: var(--text-primary);">${data.remediation_hint}</p>
            </div>
          ` : ""}
        </div>
      `;

      bindLogLinks();
    } catch (err) {
      miscResultBadge.textContent = "Error";
      miscResultBadge.className = "badge danger";
      miscResultsBody.innerHTML = `
        <div class="empty-state" style="color: var(--danger);">
          <p><strong>Diagnosis Failed:</strong> ${err.message}</p>
        </div>
      `;
    } finally {
      btnDiagnoseMisconception.disabled = false;
    }
  });

  // ---------------------------------------------------------------------------
  // 5. Tab 3: Concept Extraction Studio
  // ---------------------------------------------------------------------------
  const conceptsPresetSelect = document.getElementById("concepts-preset-select");
  const conceptsChunkText = document.getElementById("concepts-chunk-text");
  const conceptsTopK = document.getElementById("concepts-top-k");
  const btnExtractConcepts = document.getElementById("btn-extract-concepts");
  const conceptsResultsBody = document.getElementById("concepts-results-body");
  const conceptsResultBadge = document.getElementById("concepts-result-badge");

  function setConceptsPreset(key) {
    const preset = conceptsPresets[key];
    if (preset) {
      conceptsChunkText.value = preset.text;
      conceptsTopK.value = preset.top_k;
    }
  }

  conceptsPresetSelect?.addEventListener("change", (e) => setConceptsPreset(e.target.value));
  if (conceptsPresetSelect) setConceptsPreset(conceptsPresetSelect.value);

  btnExtractConcepts?.addEventListener("click", async () => {
    const rawText = conceptsChunkText.value.trim();
    const top_k = parseInt(conceptsTopK.value, 10) || 8;

    if (!rawText) {
      alert("Please provide document chunk text.");
      return;
    }

    const chunk_texts = rawText.split("---").map(c => c.trim()).filter(Boolean);

    btnExtractConcepts.disabled = true;
    conceptsResultBadge.textContent = "Extracting...";
    conceptsResultBadge.className = "badge warning";

    conceptsResultsBody.innerHTML = `
      <div class="empty-state">
        <div class="spinner"></div>
        <p style="margin-top: 1rem;">Analyzing term frequencies across ${chunk_texts.length} chunk(s)...</p>
      </div>
    `;

    try {
      const res = await fetch("/api/test/concepts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chunk_texts,
          top_k,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.error || "Concept extraction failed");

      conceptsResultBadge.textContent = "Extracted";
      conceptsResultBadge.className = "badge success";

      conceptsResultsBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="metrics-grid">
            <div class="metric-box">
              <span class="metric-label">Parsed Chunks</span>
              <span class="metric-val">${data.chunk_count}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Concepts Found</span>
              <span class="metric-val" style="color: var(--primary);">${data.concept_count}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Method</span>
              <span class="metric-val" style="font-size: 0.85rem;">TF Zero-LLM</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Log Trace</span>
              <span class="metric-val">
                <a href="#logs" class="view-log-link" data-category="concepts" data-file="${data.log_file.split('/').pop()}">${data.log_id.slice(0, 8)}</a>
              </span>
            </div>
          </div>

          <div style="padding: 14px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px;">
              Ranked Key Educational Concepts (Top ${data.concept_count})
            </div>
            <div class="pill-cloud">
              ${data.concepts.map((c, i) => `
                <div class="concept-pill">
                  <span class="rank-badge">#${i+1}</span>
                  <span>${c}</span>
                </div>
              `).join("")}
            </div>
          </div>
        </div>
      `;

      bindLogLinks();
    } catch (err) {
      conceptsResultBadge.textContent = "Error";
      conceptsResultBadge.className = "badge danger";
      conceptsResultsBody.innerHTML = `
        <div class="empty-state" style="color: var(--danger);">
          <p><strong>Extraction Failed:</strong> ${err.message}</p>
        </div>
      `;
    } finally {
      btnExtractConcepts.disabled = false;
    }
  });

  // ---------------------------------------------------------------------------
  // 6. Tab 4: Visual Suggester Studio
  // ---------------------------------------------------------------------------
  const visualsPresetSelect = document.getElementById("visuals-preset-select");
  const visualsSubject = document.getElementById("visuals-subject");
  const visualsConcept = document.getElementById("visuals-concept");
  const btnSuggestVisual = document.getElementById("btn-suggest-visual");
  const visualsResultsBody = document.getElementById("visuals-results-body");
  const visualsResultBadge = document.getElementById("visuals-result-badge");

  visualsPresetSelect?.addEventListener("change", (e) => {
    const preset = visualsPresets[e.target.value];
    if (preset) {
      visualsSubject.value = preset.subject;
      visualsConcept.value = preset.concept;
    }
  });

  btnSuggestVisual?.addEventListener("click", async () => {
    const subject = visualsSubject.value.trim();
    const concept = visualsConcept.value.trim();

    if (!subject || !concept) {
      alert("Please enter subject and concept.");
      return;
    }

    btnSuggestVisual.disabled = true;
    visualsResultBadge.textContent = "Classifying...";
    visualsResultBadge.className = "badge warning";

    visualsResultsBody.innerHTML = `
      <div class="empty-state">
        <div class="spinner"></div>
        <p style="margin-top: 1rem;">Determining visual modality for <strong>${subject}:${concept}</strong>...</p>
      </div>
    `;

    try {
      const res = await fetch("/api/test/visual_suggestion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject,
          concept,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.error || "Visual suggestion failed");

      visualsResultBadge.textContent = data.suggested_visual_type.toUpperCase();
      visualsResultBadge.className = "badge success";

      visualsResultsBody.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="metrics-grid">
            <div class="metric-box">
              <span class="metric-label">Subject</span>
              <span class="metric-val" style="font-size: 0.9rem; text-transform: uppercase;">${data.subject}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Suggested Modality</span>
              <span class="metric-val" style="color: var(--primary);">${data.suggested_visual_type.toUpperCase()}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Contract Target</span>
              <span class="metric-val" style="font-size: 0.85rem;">visual_spec.type</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Log Trace</span>
              <span class="metric-val">
                <a href="#logs" class="view-log-link" data-category="visuals" data-file="${data.log_file.split('/').pop()}">${data.log_id.slice(0, 8)}</a>
              </span>
            </div>
          </div>

          <div style="padding: 12px 14px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Decision Path</div>
            <div style="font-weight: 600; font-size: 0.9rem; margin-top: 2px;">${data.decision_path}</div>
          </div>

          <div style="padding: 12px 14px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
            <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">Downstream Integration</div>
            <p style="font-size: 0.85rem; color: var(--text-primary);">
              This modality routes directly to the <strong>${data.suggested_visual_type}_renderer.py</strong> inside the <code>avatar_voice</code> module, which will render a progressive 1344 x 1080 teaching canvas.
            </p>
          </div>
        </div>
      `;

      bindLogLinks();
    } catch (err) {
      visualsResultBadge.textContent = "Error";
      visualsResultBadge.className = "badge danger";
      visualsResultsBody.innerHTML = `
        <div class="empty-state" style="color: var(--danger);">
          <p><strong>Visual Suggestion Failed:</strong> ${err.message}</p>
        </div>
      `;
    } finally {
      btnSuggestVisual.disabled = false;
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
      metaFile.textContent = logData.source_file || "modules/ml_core/...";
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
