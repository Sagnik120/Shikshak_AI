/**
 * Small inline-SVG charts.
 *
 * Hand-rolled rather than pulled from a chart library: the app ships with no
 * build step, and these two shapes are all the analytics page needs.
 */
import { escapeHtml } from "./ui.js";

const PAD = { top: 16, right: 16, bottom: 28, left: 38 };

/** Line chart over a [{label, value}] series, with a subtle area fill. */
export function lineChart(points, { width = 720, height = 220, color = "var(--indigo-600)", unit = "%" } = {}) {
  if (!points.length) return emptyChart(width, height, "Not enough data yet");

  const plotW = width - PAD.left - PAD.right;
  const plotH = height - PAD.top - PAD.bottom;

  const values = points.map((p) => p.value);
  const max = Math.max(...values, unit === "%" ? 100 : Math.max(...values, 1));
  const min = 0;

  const x = (i) => PAD.left + (points.length === 1 ? plotW / 2 : (i / (points.length - 1)) * plotW);
  const y = (v) => PAD.top + plotH - ((v - min) / (max - min || 1)) * plotH;

  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.length - 1).toFixed(1)},${PAD.top + plotH} L${x(0).toFixed(1)},${
    PAD.top + plotH
  } Z`;

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => {
    const value = min + t * (max - min);
    return `
      <line x1="${PAD.left}" y1="${y(value)}" x2="${width - PAD.right}" y2="${y(value)}"
            stroke="var(--border)" stroke-width="1" stroke-dasharray="3 3"/>
      <text x="${PAD.left - 8}" y="${y(value) + 4}" text-anchor="end"
            font-size="10" fill="var(--text-subtle)">${Math.round(value)}</text>`;
  });

  // Label only the first, middle and last point, so the axis never collides.
  const labelIdx = [...new Set([0, Math.floor(points.length / 2), points.length - 1])];

  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}"
               role="img" aria-label="Trend chart" preserveAspectRatio="xMidYMid meet">
    <defs>
      <linearGradient id="lc-fill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${color}" stop-opacity="0.22"/>
        <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
      </linearGradient>
    </defs>
    ${ticks.join("")}
    <path d="${area}" fill="url(#lc-fill)"/>
    <path d="${line}" fill="none" stroke="${color}" stroke-width="2.5"
          stroke-linecap="round" stroke-linejoin="round"/>
    ${points
      .map(
        (p, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(p.value).toFixed(1)}" r="3.5"
            fill="var(--bg-elevated)" stroke="${color}" stroke-width="2">
            <title>${escapeHtml(p.label)}: ${p.value}${unit}</title></circle>`
      )
      .join("")}
    ${labelIdx
      .map(
        (i) => `<text x="${x(i).toFixed(1)}" y="${height - 8}" text-anchor="middle"
            font-size="10" fill="var(--text-subtle)">${escapeHtml(points[i].short || points[i].label)}</text>`
      )
      .join("")}
  </svg>`;
}

/** Horizontal bars, used for concept mastery and misconception counts. */
export function barList(items, { unit = "%", max } = {}) {
  if (!items.length) return '<p class="subtle">Nothing recorded yet.</p>';

  const ceiling = max ?? Math.max(...items.map((i) => i.value), 1);
  return items
    .map((item) => {
      const pct = Math.round((item.value / ceiling) * 100);
      const tone = item.tone || (item.value >= 75 ? "high" : item.value >= 50 ? "mid" : "low");
      return `<div class="bar-row">
          <span class="bar-label" title="${escapeHtml(item.label)}">${escapeHtml(item.label)}</span>
          <span class="bar-value">${item.value}${unit}</span>
          <span class="bar-track"><span class="bar-fill ${tone}" style="width:${pct}%"></span></span>
        </div>`;
    })
    .join("");
}

function emptyChart(width, height, message) {
  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" role="img">
    <text x="${width / 2}" y="${height / 2}" text-anchor="middle"
          font-size="13" fill="var(--text-subtle)">${escapeHtml(message)}</text>
  </svg>`;
}
