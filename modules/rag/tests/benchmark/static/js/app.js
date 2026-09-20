/**
 * RAG Performance Benchmark Dashboard — Interactive Controls & Charts
 */

const API_BASE = '';

// ─── State ─────────────────────────────────────────────
let currentReport = null;
let isRunning = false;

// ─── DOM Helpers ───────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── Init ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadSuites();
    setupEventListeners();
});

function setupEventListeners() {
    $('#runBtn').addEventListener('click', runBenchmark);
    $('#compareBtn').addEventListener('click', runComparison);
    $('#exportBtn').addEventListener('click', exportResults);
}

// ─── Load Suites ───────────────────────────────────────
async function loadSuites() {
    try {
        const res = await fetch(`${API_BASE}/api/suites`);
        const suites = await res.json();
        const select = $('#suiteSelect');
        select.innerHTML = '';
        suites.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.key;
            opt.textContent = `${s.name} (${s.num_queries} queries)`;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load suites:', e);
    }
}

// ─── Run Benchmark ─────────────────────────────────────
async function runBenchmark() {
    if (isRunning) return;
    isRunning = true;

    const btn = $('#runBtn');
    const spinner = $('#runSpinner');
    btn.disabled = true;
    spinner.classList.add('active');
    showProgress(true, 0, 'Initializing benchmark...');

    const payload = {
        suite: $('#suiteSelect').value,
        top_k: parseInt($('#topKInput').value) || 5,
        relevance_threshold: parseFloat($('#relThreshold').value) || 0.5001,
        confidence_threshold: parseFloat($('#confThreshold').value) || 0.52,
    };

    try {
        showProgress(true, 30, 'Ingesting documents and running queries...');

        const res = await fetch(`${API_BASE}/api/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Benchmark failed');
        }

        showProgress(true, 90, 'Computing metrics...');
        currentReport = await res.json();
        showProgress(true, 100, 'Complete!');

        setTimeout(() => {
            showProgress(false);
            renderReport(currentReport);
        }, 500);

    } catch (e) {
        showProgress(false);
        alert(`Benchmark failed: ${e.message}`);
    } finally {
        isRunning = false;
        btn.disabled = false;
        spinner.classList.remove('active');
    }
}

// ─── Run Comparison ────────────────────────────────────
async function runComparison() {
    if (isRunning) return;
    isRunning = true;

    const btn = $('#compareBtn');
    btn.disabled = true;
    showProgress(true, 20, 'Running A/B comparison...');

    const suite = $('#suiteSelect').value;
    const payload = {
        suite,
        config_a: { top_k: 3 },
        config_b: { top_k: 10 },
    };

    try {
        const res = await fetch(`${API_BASE}/api/compare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error('Comparison failed');

        showProgress(true, 90, 'Rendering comparison...');
        const data = await res.json();
        showProgress(false);
        renderComparison(data);

    } catch (e) {
        showProgress(false);
        alert(`Comparison failed: ${e.message}`);
    } finally {
        isRunning = false;
        btn.disabled = false;
    }
}

// ─── Export ────────────────────────────────────────────
function exportResults() {
    if (!currentReport) {
        alert('No benchmark results to export. Run a benchmark first.');
        return;
    }
    const blob = new Blob([JSON.stringify(currentReport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `benchmark_${currentReport.suite_name.replace(/\s/g, '_').toLowerCase()}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// ─── Progress Bar ──────────────────────────────────────
function showProgress(show, pct = 0, text = '') {
    const bar = $('#progressBar');
    const fill = $('#progressFill');
    const status = $('#statusText');

    if (show) {
        bar.classList.add('active');
        status.classList.add('active');
        fill.style.width = `${pct}%`;
        status.textContent = text;
    } else {
        bar.classList.remove('active');
        status.classList.remove('active');
    }
}

// ─── Render Report ─────────────────────────────────────
function renderReport(report) {
    const container = $('#resultsArea');
    container.innerHTML = '';
    container.classList.add('animate-in');

    // Quality Scorecard
    container.innerHTML += renderQualityMetrics(report);

    // Latency Section
    container.innerHTML += renderLatencySection(report);

    // Stage Breakdown Chart
    container.innerHTML += renderStageChart(report);

    // Per-Query Results Table
    container.innerHTML += renderQueryTable(report);
}

function renderQualityMetrics(report) {
    const m = report.metrics;
    const t = report.production_targets || {};

    const cards = [
        { label: 'Precision@K', value: m.precision_at_k, target: '≥ 0.60', pass: t.precision_at_k },
        { label: 'Recall@K', value: m.recall_at_k, target: '≥ 0.50', pass: t.recall_at_k },
        { label: 'MRR', value: m.mrr, target: '≥ 0.70', pass: t.mrr },
        { label: 'NDCG@K', value: m.ndcg_at_k, target: '≥ 0.60', pass: t.ndcg_at_k },
        { label: 'Risk Accuracy', value: m.risk_accuracy, target: '≥ 0.90', pass: t.risk_accuracy },
    ];

    let html = `
        <div class="metrics-section">
            <div class="section-title">🎯 Retrieval Quality Scorecard — ${report.suite_name}</div>
            <div class="metrics-grid">
    `;

    cards.forEach(c => {
        const cls = c.pass ? 'pass' : 'fail';
        const badge = c.pass ? '✓ PASS' : '✗ FAIL';
        html += `
            <div class="metric-card ${cls}">
                <div class="metric-value">${(c.value * 100).toFixed(1)}%</div>
                <div class="metric-label">${c.label}</div>
                <div class="metric-target">Target: ${c.target}</div>
                <div class="metric-badge ${cls}">${badge}</div>
            </div>
        `;
    });

    html += '</div></div>';
    return html;
}

function renderLatencySection(report) {
    const l = report.latency;
    const t = report.production_targets || {};

    const cards = [
        { label: 'P50 Latency', value: `${l.p50_ms.toFixed(1)}ms`, raw: l.p50_ms },
        { label: 'P95 Latency', value: `${l.p95_ms.toFixed(1)}ms`, raw: l.p95_ms, pass: t.latency_p95, target: '≤ 500ms' },
        { label: 'P99 Latency', value: `${l.p99_ms.toFixed(1)}ms`, raw: l.p99_ms },
        { label: 'Mean Latency', value: `${l.mean_ms.toFixed(1)}ms`, raw: l.mean_ms },
        { label: 'Throughput', value: `${l.throughput_qps.toFixed(1)} QPS`, raw: l.throughput_qps },
    ];

    let html = `
        <div class="metrics-section">
            <div class="section-title">⚡ Latency & Throughput</div>
            <div class="metrics-grid">
    `;

    cards.forEach(c => {
        const cls = c.pass !== undefined ? (c.pass ? 'pass' : 'fail') : '';
        const badge = c.pass !== undefined ? (c.pass ? '✓ PASS' : '✗ FAIL') : '';
        html += `
            <div class="metric-card ${cls}">
                <div class="metric-value">${c.value}</div>
                <div class="metric-label">${c.label}</div>
                ${c.target ? `<div class="metric-target">Target: ${c.target}</div>` : ''}
                ${badge ? `<div class="metric-badge ${cls}">${badge}</div>` : ''}
            </div>
        `;
    });

    html += '</div></div>';
    return html;
}

function renderStageChart(report) {
    const stages = report.stage_breakdown || {};
    const entries = Object.entries(stages).filter(([k]) => k !== 'total_ms');

    if (entries.length === 0) return '';

    const maxVal = Math.max(...entries.map(([, v]) => v), 1);

    let bars = '';
    const colors = ['#4f46e5', '#0284c7', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0d9488'];

    entries.forEach(([name, ms], i) => {
        const h = Math.max(4, (ms / maxVal) * 180);
        const color = colors[i % colors.length];
        bars += `
            <div class="bar-group">
                <div class="bar-value">${ms.toFixed(1)}ms</div>
                <div class="bar" style="height:${h}px; background:${color};"></div>
                <div class="bar-label">${name.replace(/_/g, ' ')}</div>
            </div>
        `;
    });

    return `
        <div class="chart-container">
            <div class="chart-title">📊 Pipeline Stage Latency Breakdown (avg per query)</div>
            <div class="bar-chart">${bars}</div>
        </div>
    `;
}

function renderQueryTable(report) {
    const queries = report.per_query || [];
    if (queries.length === 0) return '';

    let rows = '';
    queries.forEach((q, i) => {
        const riskCls = q.risk_level.replace(/\s/g, '_');
        const riskLabel = q.risk_level.replace(/_/g, ' ');
        const riskMatch = q.risk_match ? '✓' : '✗';
        const topScore = q.retrieved_scores.length > 0 ? q.retrieved_scores[0].toFixed(4) : '—';

        rows += `
            <tr>
                <td>${i + 1}</td>
                <td title="${q.query_text}">${q.query_text.length > 50 ? q.query_text.slice(0, 50) + '…' : q.query_text}</td>
                <td class="score-pill">${(q.precision_at_k * 100).toFixed(0)}%</td>
                <td class="score-pill">${(q.recall_at_k * 100).toFixed(0)}%</td>
                <td class="score-pill">${q.reciprocal_rank.toFixed(3)}</td>
                <td>${topScore}</td>
                <td><span class="risk-badge ${riskCls}">${riskLabel}</span></td>
                <td>${riskMatch}</td>
                <td>${q.latency_ms.toFixed(1)}ms</td>
                <td>${q.retrieved_chunk_ids.length}</td>
            </tr>
        `;
    });

    return `
        <div class="results-table-container">
            <div style="padding:16px 20px; border-bottom:1px solid var(--border);">
                <div class="chart-title" style="margin-bottom:0;">📋 Per-Query Results (${queries.length} queries)</div>
            </div>
            <div style="overflow-x:auto;">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Query</th>
                            <th>P@K</th>
                            <th>R@K</th>
                            <th>RR</th>
                            <th>Top Score</th>
                            <th>Risk Level</th>
                            <th>Risk ✓</th>
                            <th>Latency</th>
                            <th>Chunks</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>
    `;
}

// ─── Render Comparison ─────────────────────────────────
function renderComparison(data) {
    const container = $('#resultsArea');
    container.innerHTML = '';
    container.classList.add('animate-in');

    const configA = JSON.stringify(data.config_a);
    const configB = JSON.stringify(data.config_b);

    container.innerHTML = `
        <div class="section-title">🔄 A/B Comparison: ${data.report_a.suite_name}</div>
        <div class="two-col">
            <div>
                <h3 style="font-size:14px;margin-bottom:12px;color:var(--accent);">Config A: ${configA}</h3>
                ${renderQualityMetrics(data.report_a)}
                ${renderLatencySection(data.report_a)}
            </div>
            <div>
                <h3 style="font-size:14px;margin-bottom:12px;color:var(--info);">Config B: ${configB}</h3>
                ${renderQualityMetrics(data.report_b)}
                ${renderLatencySection(data.report_b)}
            </div>
        </div>
    `;
}
