/**
 * Shikshak AI — Post-Lesson Report Controller (report.html)
 */

import { render } from "./render.js";

document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  const topicParam = urlParams.get("topic");

  const reportTitle = document.getElementById("report-title");
  if (topicParam && reportTitle) {
    reportTitle.textContent = `${topicParam}, untangled.`;
  }

  const scoreRing = document.getElementById("score-ring");
  const scoreNumber = document.getElementById("score-number");
  const btnDownloadReport = document.getElementById("btn-download-report");

  const targetScore = parseInt(urlParams.get("score")) || 78;
  const circumference = 2 * Math.PI * 60; // ~376.99
  const targetOffset = circumference - (circumference * targetScore) / 100;

  // 1. Animate SVG Circle and Counter (0 -> 78)
  setTimeout(() => {
    scoreRing.style.strokeDashoffset = targetOffset.toString();

    let current = 0;
    const duration = 1200;
    const startTime = performance.now();

    function step(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const ease = 1 - Math.pow(1 - progress, 3);
      current = Math.round(ease * targetScore);
      scoreNumber.textContent = current.toString();

      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }
    requestAnimationFrame(step);
  }, 200);

  // 2. Download Report Button Action
  btnDownloadReport.addEventListener("click", () => {
    btnDownloadReport.disabled = true;
    btnDownloadReport.innerHTML = `${render.getSpinnerSvg()} <span>Generating PDF...</span>`;

    setTimeout(() => {
      btnDownloadReport.disabled = false;
      btnDownloadReport.innerHTML = `<span>✓ Report Saved</span>`;
      render.showToast("Lesson report saved to Downloads: Shikshak_Report_Cell_Structure.pdf");

      setTimeout(() => {
        btnDownloadReport.innerHTML = `<span>Download report (PDF)</span>`;
      }, 3000);
    }, 1200);
  });

  // 3. Next Steps Card Interactions
  const stepReviewNotes = document.getElementById("step-review-notes");
  if (stepReviewNotes) {
    stepReviewNotes.addEventListener("click", () => {
      render.showToast("Opening saved notes from Cell Structure lesson...");
    });
  }

  const stepActiveTransport = document.getElementById("step-active-transport");
  if (stepActiveTransport) {
    stepActiveTransport.addEventListener("click", () => {
      render.showToast("Next lesson queued: Active Transport & ATP Pumps.");
      setTimeout(() => {
        window.location.href = "classroom.html?mode=mock&topic=Active+Transport";
      }, 1000);
    });
  }
});
