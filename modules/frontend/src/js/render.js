/**
 * Shikshak AI — UI Render Components & Helpers
 * Contains SVG branding, badge generators, toast messaging, and formatting tools.
 */

export const render = {
  getSignalLogoSvg() {
    return `
      <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M7 16C7 11.0294 11.0294 7 16 7" stroke="#2A3FA0" stroke-width="3" stroke-linecap="round"/>
        <path d="M25 16C25 20.9706 20.9706 25 16 25" stroke="#0FA3A3" stroke-width="3" stroke-linecap="round"/>
        <circle cx="16" cy="16" r="3.5" fill="#2A3FA0"/>
      </svg>
    `;
  },

  getCheckmarkSvg() {
    return `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
    `;
  },

  getSpinnerSvg() {
    return `
      <svg class="spinner-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
        <path d="M12 2a10 10 0 0 1 10 10"/>
      </svg>
    `;
  },

  showToast(message, type = "success") {
    let toast = document.getElementById("global-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "global-toast";
      toast.className = "toast";
      document.body.appendChild(toast);
    }
    const icon = type === "success" ? this.getCheckmarkSvg() : "ℹ";
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toast.classList.add("show");
    setTimeout(() => {
      toast.classList.remove("show");
    }, 3500);
  },

  formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  }
};
