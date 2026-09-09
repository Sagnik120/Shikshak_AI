// Shikshak AI — RAG Web Testbed Client Application
// Light Professional Theme Interactivity & API Connector

let uploadedFileObj = null;
let currentCategory = "all";

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initDropzone();
  checkServerStatus();
  loadLogs("all");
});

// ----------------------------------------------------------------------------
// Tab Switching
// ----------------------------------------------------------------------------
function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTabId = btn.getAttribute("data-tab");

      tabButtons.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(targetTabId);
      if (targetPane) {
        targetPane.classList.add("active");
      }

      if (targetTabId === "tab-logs") {
        loadLogs(currentCategory);
      }
    });
  });
}

// ----------------------------------------------------------------------------
// File Dropzone Handling
// ----------------------------------------------------------------------------
function initDropzone() {
  const dropzone = document.getElementById("file-dropzone");
  const fileInput = document.getElementById("file-input");

  if (!dropzone || !fileInput) return;

  ["dragenter", "dragover"].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.style.borderColor = "var(--primary)";
      dropzone.style.backgroundColor = "var(--primary-subtle)";
    }, false);
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.style.borderColor = "#cbd5e1";
      dropzone.style.backgroundColor = "var(--bg-subtle)";
    }, false);
  });

  dropzone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      handleSelectedFile(files[0]);
    }
  }, false);
}

function handleFileSelected(input) {
  if (input.files && input.files.length > 0) {
    handleSelectedFile(input.files[0]);
  }
}

function handleSelectedFile(file) {
  uploadedFileObj = file;
  const label = document.getElementById("dropzone-label");
  const filenameInput = document.getElementById("parse-filename");
  if (label) {
    label.innerHTML = `Selected File: <strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
  }
  if (filenameInput) {
    filenameInput.value = file.name;
  }
}

// ----------------------------------------------------------------------------
// Server Status & Document Cache Manifest
// ----------------------------------------------------------------------------
async function checkServerStatus() {
  try {
    const res = await fetch("/api/test/status");
    if (!res.ok) return;
    const data = await res.json();

    const adapterBadge = document.getElementById("adapter-badge");
    if (adapterBadge && data.embedding_adapter) {
      adapterBadge.innerHTML = `<span>Adapter: ${data.embedding_adapter}</span>`;
    }

    // Refresh doc select options
    refreshDocSelectOptions(data.cached_documents || []);
  } catch (err) {
    console.warn("Server status check failed:", err);
  }
}

function refreshDocSelectOptions(docs) {
  const retrieveSelect = document.getElementById("retrieve-doc-select");
  const groundingSelect = document.getElementById("grounding-doc-select");

  const buildOptions = () => {
    let html = `<option value="topic_only">⭐ Topic-Only Mode (document_id=None)</option>`;
    docs.forEach(d => {
      const label = d.chapters && d.chapters.length > 0 ? d.chapters[0] : d.document_id;
      html += `<option value="${d.document_id}">${label} (${d.document_id} | ${d.chunk_count} chunks)</option>`;
    });
    return html;
  };

  const optionsHtml = buildOptions();
  if (retrieveSelect) retrieveSelect.innerHTML = optionsHtml;
  if (groundingSelect) groundingSelect.innerHTML = optionsHtml;
}

// ----------------------------------------------------------------------------
// Sample Document Pre-fills
// ----------------------------------------------------------------------------
const PRESETS = {
  physics: `Chapter 12: Electricity and Ohm's Law

12.1 Electric Current and Circuit
An electric current is expressed by the amount of charge flowing through a particular area in unit time. It is the rate of flow of electric charges. Electrons constitute the flow of charges in metallic conductors.

12.2 Electric Potential and Potential Difference
Electric potential difference between two points in an electric circuit carrying current is the work done to move a unit charge from one point to another: V = W / Q. The SI unit is volt (V).

12.3 Ohm's Law
German physicist Georg Simon Ohm found that current (I) is directly proportional to potential difference (V) across conductor terminals at constant temperature: V = I * R. The SI unit of resistance is ohm (Ω).`,

  hindi: `अध्याय 10: प्रकाश – परावर्तन तथा अपवर्तन

10.1 प्रकाश का परावर्तन
उच्च कोटि की पॉलिश किया हुआ पृष्ठ, जैसे कि दर्पण, अपने पर पड़ने वाले अधिकांश प्रकाश को परावर्तित कर देता है। प्रकाश के परावर्तन के दो नियम हैं:
(i) आपतन कोण, परावर्तन कोण के बराबर होता है।
(ii) आपतित किरण, दर्पण के आपतन बिंदु पर अभिलंब तथा परावर्तित किरण, ये सभी एक ही तल में होते हैं।

10.2 गोलीय दर्पण
ऐसे दर्पण जिनका परावर्तक पृष्ठ गोलीय है, गोलीय दर्पण कहलाते हैं। अवतल दर्पण का पृष्ठ अंदर की ओर तथा उत्तल दर्पण का पृष्ठ बाहर की ओर वक्रित होता है। सूत्र: R = 2f.`
};

function loadSampleDoc(type) {
  const textInput = document.getElementById("parse-text-input");
  const filenameInput = document.getElementById("parse-filename");
  if (PRESETS[type]) {
    if (textInput) textInput.value = PRESETS[type];
    if (filenameInput) filenameInput.value = type === "physics" ? "Physics_Ohm_Law.txt" : "Hindi_NCERT_Light.txt";
    uploadedFileObj = null;
    const label = document.getElementById("dropzone-label");
    if (label) label.textContent = "Click or Drag & Drop .pdf, .docx, .pptx, or .txt file";
  }
}

// ----------------------------------------------------------------------------
// Tab 1: Run Document Parsing & Ingestion
// ----------------------------------------------------------------------------
async function runDocumentParse() {
  const textInput = document.getElementById("parse-text-input");
  const filenameInput = document.getElementById("parse-filename");
  const warningContainer = document.getElementById("parse-warning-container");

  const formData = new FormData();
  if (uploadedFileObj) {
    formData.append("file", uploadedFileObj);
  } else if (textInput && textInput.value.trim()) {
    formData.append("raw_text", textInput.value.trim());
    formData.append("filename", filenameInput ? filenameInput.value : "pasted_notes.txt");
  } else {
    alert("Please upload a file or paste text to parse.");
    return;
  }

  try {
    const res = await fetch("/api/test/parse", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Parse failed");
    }

    const data = await res.json();

    // Render Warnings if any
    if (warningContainer) {
      if (data.warnings && data.warnings.length > 0) {
        warningContainer.innerHTML = data.warnings.map(w => `
          <div class="alert alert-warning">
            <div>
              <div class="alert-title">Diagnostic Warning</div>
              <div>${w}</div>
            </div>
          </div>
        `).join("");
      } else {
        warningContainer.innerHTML = "";
      }
    }

    // Render Meta Tags
    const metaTags = document.getElementById("parse-meta-tags");
    if (metaTags) {
      metaTags.innerHTML = `
        <span class="chip chip-primary">Doc ID: ${data.document_id}</span>
        <span class="chip chip-success">Lang: ${data.source_lang.toUpperCase()}</span>
        <span class="chip">Total Chunks: ${data.chunk_count}</span>
      `;
    }

    // Render Chapters
    const chaptersBox = document.getElementById("parse-chapters-box");
    if (chaptersBox) {
      if (data.chapters && data.chapters.length > 0) {
        chaptersBox.textContent = data.chapters.map((c, i) => `${i + 1}. ${c}`).join("\n");
      } else {
        chaptersBox.textContent = "No explicit chapter headings detected (flat section structure).";
      }
    }

    // Render Key Terms
    const keytermsBox = document.getElementById("parse-keyterms-box");
    if (keytermsBox) {
      if (data.key_terms && data.key_terms.length > 0) {
        keytermsBox.innerHTML = data.key_terms.map(t => `<span class="chip chip-primary">${t}</span>`).join(" ");
      } else {
        keytermsBox.innerHTML = `<span class="chip">No terms extracted</span>`;
      }
    }

    // Render Chunks Preview
    const chunksBox = document.getElementById("parse-chunks-box");
    if (chunksBox && data.chunks_sample) {
      chunksBox.textContent = JSON.stringify(data.chunks_sample, null, 2);
    }

    // Refresh status so Retrieval tab has the new document
    checkServerStatus();

  } catch (err) {
    alert("Parsing error: " + err.message);
  }
}

// ----------------------------------------------------------------------------
// Tab 2: Test Semantic Chunker
// ----------------------------------------------------------------------------
async function runChunkTest() {
  const textInput = document.getElementById("chunk-text-input");
  const targetInput = document.getElementById("chunk-target");
  const maxInput = document.getElementById("chunk-max");
  const overlapInput = document.getElementById("chunk-overlap");
  const tableBody = document.querySelector("#chunk-table tbody");
  const summaryChips = document.getElementById("chunk-summary-chips");

  const text = textInput ? textInput.value.trim() : "";
  if (!text) {
    alert("Please enter text to chunk.");
    return;
  }

  try {
    const res = await fetch("/api/test/chunk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text,
        target_tokens: parseInt(targetInput ? targetInput.value : 300),
        max_tokens: parseInt(maxInput ? maxInput.value : 500),
        overlap_pct: parseFloat(overlapInput ? overlapInput.value : 0.15)
      })
    });

    if (!res.ok) throw new Error("Chunking failed");
    const data = await res.json();

    if (summaryChips) {
      summaryChips.innerHTML = `
        <span class="chip chip-primary">Input Tokens: ${data.total_input_tokens}</span>
        <span class="chip chip-success">Generated Chunks: ${data.total_chunks}</span>
      `;
    }

    if (tableBody) {
      tableBody.innerHTML = data.chunks.map(c => `
        <tr>
          <td><strong>#${c.chunk_index}</strong></td>
          <td>${c.token_count}</td>
          <td>${c.word_count}</td>
          <td>
            <span class="chip ${c.satisfies_budget ? 'chip-success' : 'chip-danger'}">
              ${c.satisfies_budget ? '≤ 500 Tokens (Valid)' : 'Budget Breach'}
            </span>
          </td>
          <td><div style="max-height: 80px; overflow-y: auto; font-size: 12px;">${c.text}</div></td>
        </tr>
      `).join("");
    }

  } catch (err) {
    alert("Chunking error: " + err.message);
  }
}

// ----------------------------------------------------------------------------
// Tab 3: Test Embeddings
// ----------------------------------------------------------------------------
async function runEmbedTest() {
  const textInput = document.getElementById("embed-text-input");
  const resultsContainer = document.getElementById("embed-results-container");

  const rawLines = textInput ? textInput.value.split("\n").map(s => s.trim()).filter(Boolean) : [];
  if (rawLines.length === 0) {
    alert("Please enter at least one line of text to embed.");
    return;
  }

  try {
    const res = await fetch("/api/test/embed", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texts: rawLines })
    });

    if (!res.ok) throw new Error("Embedding generation failed");
    const data = await res.json();

    if (resultsContainer) {
      resultsContainer.textContent = JSON.stringify(data, null, 2);
    }
  } catch (err) {
    alert("Embedding error: " + err.message);
  }
}

// ----------------------------------------------------------------------------
// Tab 4: Test Hybrid Retrieval
// ----------------------------------------------------------------------------
async function runRetrievalTest() {
  const queryInput = document.getElementById("retrieve-query");
  const docSelect = document.getElementById("retrieve-doc-select");
  const topkInput = document.getElementById("retrieve-topk");
  const floorInput = document.getElementById("retrieve-floor");
  const confInput = document.getElementById("retrieve-conf");
  const tableBody = document.querySelector("#retrieve-table tbody");
  const riskBadge = document.getElementById("retrieve-risk-badge");

  const queryText = queryInput ? queryInput.value.trim() : "";
  if (!queryText) {
    alert("Please enter a query string.");
    return;
  }

  try {
    const res = await fetch("/api/test/retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: docSelect ? docSelect.value : null,
        query_text: queryText,
        top_k: parseInt(topkInput ? topkInput.value : 5),
        relevance_threshold: parseFloat(floorInput ? floorInput.value : 0.5001),
        confidence_threshold: parseFloat(confInput ? confInput.value : 0.52)
      })
    });

    if (!res.ok) throw new Error("Retrieval failed");
    const data = await res.json();

    // Render Risk Level Badge
    if (riskBadge) {
      let chipClass = "chip-success";
      if (data.risk_level === "high_hallucination_risk") chipClass = "chip-danger";
      else if (data.risk_level === "moderate_relevance") chipClass = "chip-primary";

      riskBadge.innerHTML = `<span class="chip ${chipClass}">Risk: ${data.risk_level.toUpperCase()}</span>`;
    }

    if (tableBody) {
      if (!data.candidates || data.candidates.length === 0) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="6" style="text-align: center; color: var(--danger); font-weight: 600; padding: 24px;">
              No candidates passed relevance threshold (0.5001 floor). Flagged as ${data.risk_level}.
            </td>
          </tr>
        `;
      } else {
        tableBody.innerHTML = data.candidates.map(c => `
          <tr>
            <td><code>${c.chunk_id}</code></td>
            <td>${c.section_title || '—'}</td>
            <td><strong>${c.reranker_score}</strong></td>
            <td>${c.dense_score !== null ? c.dense_score : '—'}</td>
            <td>${c.sparse_score !== null ? c.sparse_score : '—'}</td>
            <td><div style="max-height: 90px; overflow-y: auto; font-size: 12px;">${c.text}</div></td>
          </tr>
        `).join("");
      }
    }

  } catch (err) {
    alert("Retrieval error: " + err.message);
  }
}

function testOutOfScopeQuery() {
  const queryInput = document.getElementById("retrieve-query");
  if (queryInput) {
    queryInput.value = "Explain light-dependent reactions of photosynthesis in chloroplast thylakoids.";
  }
  runRetrievalTest();
}

// ----------------------------------------------------------------------------
// Tab 5: Grounding & Hallucination Audit
// ----------------------------------------------------------------------------
const SIMULATED_RESPONSES = {
  valid: `Ohm's Law states that electric current is directly proportional to the potential difference across a conductor at constant temperature, represented mathematically as V = I * R.

grounded_on: ["chunk_doc_phys_0001", "chunk_doc_phys_0003"]`,

  hallucinated: `Ohm's Law was discovered in 1827 and involves magnetic flux density and Maxwell equations.

grounded_on: ["chunk_fake_nonexistent_9999", "chunk_hallucinated_1234"]`,

  empty: `Here is a generic explanation of resistance and voltage without citing any provided document chunks.

grounded_on: []`
};

function prefillTeacherResponse(type) {
  const teacherInput = document.getElementById("grounding-teacher-response");
  if (teacherInput && SIMULATED_RESPONSES[type]) {
    teacherInput.value = SIMULATED_RESPONSES[type];
  }
}

async function runGroundingAudit() {
  const queryInput = document.getElementById("grounding-query");
  const docSelect = document.getElementById("grounding-doc-select");
  const teacherInput = document.getElementById("grounding-teacher-response");

  const promptBox = document.getElementById("grounding-prompt-box");
  const cleanBox = document.getElementById("clean-explanation-box");
  const citedIdsContainer = document.getElementById("cited-ids-container");
  const bannerContainer = document.getElementById("hallucination-banner-container");

  const queryText = queryInput ? queryInput.value.trim() : "";
  if (!queryText) {
    alert("Please enter a question or concept.");
    return;
  }

  try {
    const res = await fetch("/api/test/grounding", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: docSelect ? docSelect.value : null,
        query_text: queryText,
        simulated_teacher_response: teacherInput ? teacherInput.value.trim() : null
      })
    });

    if (!res.ok) throw new Error("Grounding audit failed");
    const data = await res.json();

    // 1. Display Prompt
    if (promptBox) {
      promptBox.textContent = data.prompt_context;
    }

    const audit = data.citation_audit;

    // 2. Display Cleaned Explanation
    if (cleanBox) {
      cleanBox.textContent = audit.clean_teacher_explanation || "No simulated teacher response provided.";
    }

    // 3. Display Cited IDs
    if (citedIdsContainer) {
      if (audit.cited_chunk_ids && audit.cited_chunk_ids.length > 0) {
        citedIdsContainer.innerHTML = audit.cited_chunk_ids.map(id => `
          <span class="chip chip-primary">${id}</span>
        `).join(" ");
      } else {
        citedIdsContainer.innerHTML = `<span class="chip">grounded_on: [] (No chunks cited)</span>`;
      }
    }

    // 4. Hallucination Callout Banner
    if (bannerContainer) {
      if (audit.is_hallucinating) {
        bannerContainer.innerHTML = `
          <div class="hallucination-card">
            <div class="hallucination-header">
              <span>⚠️ Hallucination Risk Detected</span>
              <span class="source-tag">${audit.hallucination_source_file} :: ${audit.hallucination_source_function}()</span>
            </div>
            <div style="font-size: 13.5px; color: #881337; margin-bottom: 6px;">
              <strong>Signal:</strong> ${audit.risk_signal}
            </div>
            <div style="font-size: 12.5px; color: #9f1239;">
              Valid Context IDs were: <code>${JSON.stringify(data.candidate_chunk_ids)}</code>
            </div>
          </div>
        `;
      } else {
        bannerContainer.innerHTML = `
          <div class="alert alert-success">
            <div>
              <div class="alert-title">Citation Verification Passed</div>
              <div>All cited source chunks trace to high-confidence excerpts in the grounding context.</div>
            </div>
          </div>
        `;
      }
    }

  } catch (err) {
    alert("Grounding audit error: " + err.message);
  }
}

// ----------------------------------------------------------------------------
// Tab 6: Structured Logs
// ----------------------------------------------------------------------------
async function loadLogs(category) {
  currentCategory = category;
  const tableBody = document.querySelector("#logs-table tbody");
  if (!tableBody) return;

  tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">Loading logs...</td></tr>`;

  try {
    const url = category === "all" ? "/api/test/logs" : `/api/test/logs?category=${category}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch logs");
    const data = await res.json();

    if (!data.logs || data.logs.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No log files found in category '${category}'.</td></tr>`;
      return;
    }

    tableBody.innerHTML = data.logs.map(log => `
      <tr>
        <td style="white-space: nowrap; font-size: 12px;">${log.timestamp.replace("T", " ").slice(0, 19)}</td>
        <td><span class="chip chip-primary">${log.category.toUpperCase()}</span></td>
        <td><code>${log.run_id}</code></td>
        <td style="font-size: 12px;">${log.source_file}</td>
        <td><strong>${log.function_name}()</strong></td>
        <td>${log.duration_ms} ms</td>
        <td>
          <span class="chip ${log.is_hallucinating ? 'chip-danger' : 'chip-success'}">
            ${log.is_hallucinating ? '⚠️ Alert' : 'Normal'}
          </span>
        </td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 12px;" onclick="viewLogDetail('${log.category}', '${log.filename}')">
            View JSON
          </button>
        </td>
      </tr>
    `).join("");

  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--danger);">Failed to load logs: ${err.message}</td></tr>`;
  }
}

async function viewLogDetail(category, filename) {
  const modal = document.getElementById("log-modal");
  const modalTitle = document.getElementById("modal-log-title");
  const modalContent = document.getElementById("modal-log-content");

  try {
    const res = await fetch(`/api/test/logs/${category}/${filename}`);
    if (!res.ok) throw new Error("Log detail not found");
    const data = await res.json();

    if (modalTitle) modalTitle.textContent = `Diagnostic Log: ${filename}`;
    if (modalContent) modalContent.textContent = JSON.stringify(data, null, 2);
    if (modal) modal.classList.add("active");
  } catch (err) {
    alert("Error viewing log: " + err.message);
  }
}

function closeLogModal() {
  const modal = document.getElementById("log-modal");
  if (modal) modal.classList.remove("active");
}
