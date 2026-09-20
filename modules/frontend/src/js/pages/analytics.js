/** Progress analytics: accuracy trend, concept strength, misconceptions, time. */
import { api } from "../api.js";
import {
  $, el, clear, escapeHtml, requireAuth, mountHeader, formatDuration, emptyState,
} from "../ui.js";
import { lineChart, barList } from "../charts.js";

const user = await requireAuth();
if (user) {
  mountHeader(user, "/analytics.html");
  const root = $("#analytics-root");

  try {
    render(await api.analytics());
  } catch (error) {
    clear(root).append(
      emptyState("alert", "Couldn't load your analytics", error.message,
        el("button", { class: "btn btn-primary", onclick: () => window.location.reload() }, "Try again"))
    );
  }

  function render(data) {
    clear(root);

    if (!data.totals.questions && !data.totals.lessons) {
      root.append(
        emptyState(
          "chart",
          "Nothing to chart yet",
          "Finish a lesson and your accuracy, mastery and time-on-task will appear here.",
          el("a", { class: "btn btn-primary", href: "/new-lesson.html" }, "Start a lesson")
        )
      );
      return;
    }

    root.append(totals(data.totals, data.response_time), accuracySection(data), conceptSection(data), bottomGrid(data));
  }

  function totals(t, responseTime) {
    const accuracy = t.questions ? Math.round((t.correct / t.questions) * 100) : 0;
    const grid = el("div", { class: "stat-grid", style: "margin-bottom:var(--sp-5)" });
    grid.innerHTML = [
      { label: "Lessons completed", value: t.completed, meta: `${t.lessons} built in total` },
      { label: "Overall accuracy", value: `${accuracy}%`, meta: `${t.correct} of ${t.questions} correct` },
      { label: "Time learning", value: formatDuration(t.learning_minutes), meta: "across all lessons" },
      {
        label: "Avg. thinking time",
        value: `${responseTime.average_sec}s`,
        meta: `${responseTime.samples} answers measured`,
      },
    ]
      .map(
        (c) => `<div class="stat">
          <div class="stat-label">${escapeHtml(c.label)}</div>
          <div class="stat-value">${escapeHtml(String(c.value))}</div>
          <div class="stat-meta">${escapeHtml(c.meta)}</div>
        </div>`
      )
      .join("");
    return grid;
  }

  function accuracySection(data) {
    const card = el("section", { class: "card", style: "margin-bottom:var(--sp-5)" });
    const points = data.accuracy_trend.map((d) => ({
      label: d.date,
      short: d.date.slice(5),
      value: d.accuracy_pct,
    }));

    card.innerHTML = `
      <div class="card-header">
        <h2 class="card-title">Accuracy over time</h2>
        <span class="subtle">${points.length} day${points.length === 1 ? "" : "s"} with activity</span>
      </div>
      <div class="card-body">
        <div class="chart-wrap">${lineChart(points, { unit: "%" })}</div>
      </div>`;
    return card;
  }

  function conceptSection(data) {
    const card = el("section", { class: "card", style: "margin-bottom:var(--sp-5)" });
    card.innerHTML = `
      <div class="card-header"><h2 class="card-title">Concept strength</h2>
        <span class="subtle">${data.concept_strength.length} concepts studied</span></div>
      <div class="card-body">
        <div class="grid grid-2" style="gap:var(--sp-8)">
          <div>
            <div class="section-label" style="margin-bottom:var(--sp-4)">Needs the most work</div>
            ${barList(
              data.weakest.map((c) => ({ label: c.concept, value: Math.round(c.mastery_pct) })),
              { unit: "%", max: 100 }
            )}
          </div>
          <div>
            <div class="section-label" style="margin-bottom:var(--sp-4)">Strongest</div>
            ${barList(
              data.strongest.map((c) => ({ label: c.concept, value: Math.round(c.mastery_pct) })),
              { unit: "%", max: 100 }
            )}
          </div>
        </div>
      </div>`;
    return card;
  }

  function bottomGrid(data) {
    const grid = el("div", { class: "grid grid-2" });

    const misconceptions = el("section", { class: "card" });
    misconceptions.innerHTML = `
      <div class="card-header"><h2 class="card-title">Recurring misconceptions</h2></div>
      <div class="card-body">
        ${
          data.misconceptions.length
            ? barList(
                data.misconceptions.map((m) => ({ label: m.tag, value: m.count, tone: "low" })),
                { unit: "×" }
              )
            : '<p class="subtle">No repeated misconceptions detected — your wrong answers haven\'t clustered into a pattern.</p>'
        }
      </div>`;

    const time = el("section", { class: "card" });
    const points = data.time_on_task.map((d) => ({
      label: d.date,
      short: d.date.slice(5),
      value: d.minutes,
    }));
    time.innerHTML = `
      <div class="card-header"><h2 class="card-title">Time on task</h2>
        <span class="subtle">minutes per day</span></div>
      <div class="card-body">
        <div class="chart-wrap">${lineChart(points, { height: 180, color: "var(--teal-600)", unit: " min" })}</div>
      </div>`;

    grid.append(misconceptions, time);
    return grid;
  }
}
