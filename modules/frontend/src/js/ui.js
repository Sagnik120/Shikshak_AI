/**
 * Shikshak AI — shared UI helpers: DOM, formatting, toasts, header, guards.
 */

import { api, tokens } from "./api.js";

/* -------------------------------------------------------------------------
   DOM
   ------------------------------------------------------------------------- */

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

/** Escape text destined for an innerHTML template. */
export function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

/* -------------------------------------------------------------------------
   Formatting
   ------------------------------------------------------------------------- */

export function formatDate(iso, opts = {}) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric", ...opts });
}

export function formatRelative(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  const seconds = (Date.now() - date.getTime()) / 1000;
  if (Number.isNaN(seconds)) return "—";
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} d ago`;
  return formatDate(iso);
}

/** "1 session" / "3 sessions" — pass a custom plural for irregular words. */
export function plural(count, singular, pluralForm) {
  const word = count === 1 ? singular : pluralForm ?? `${singular}s`;
  return `${count} ${word}`;
}

export function formatDuration(minutes) {
  const value = Number(minutes) || 0;
  if (value <= 0) return "0 min";
  if (value < 1) return "< 1 min";
  if (value < 60) return `${Math.round(value)} min`;
  const hours = Math.floor(value / 60);
  const rest = Math.round(value % 60);
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

export function formatSeconds(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  const mins = String(Math.floor(total / 60)).padStart(2, "0");
  const secs = String(total % 60).padStart(2, "0");
  return `${mins}:${secs}`;
}

export const LEVEL_LABELS = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced" };
export const LANGUAGE_LABELS = { en: "English", hi: "हिन्दी", bn: "বাংলা" };

export const STATUS_META = {
  created: { label: "Draft", cls: "badge" },
  planned: { label: "Ready", cls: "badge badge-accent" },
  in_progress: { label: "In progress", cls: "badge badge-amber" },
  completed: { label: "Completed", cls: "badge badge-green" },
  escalated: { label: "Needs a teacher", cls: "badge badge-rose" },
  abandoned: { label: "Abandoned", cls: "badge" },
};

export function scoreClass(score) {
  if (score >= 75) return "high";
  if (score >= 50) return "mid";
  return "low";
}

/* -------------------------------------------------------------------------
   Toasts
   ------------------------------------------------------------------------- */

function toastStack() {
  let stack = $(".toast-stack");
  if (!stack) {
    stack = el("div", { class: "toast-stack", role: "status", "aria-live": "polite" });
    document.body.append(stack);
  }
  return stack;
}

export function toast(message, variant = "info", ms = 4200) {
  const node = el("div", { class: `toast ${variant}` }, message);
  toastStack().append(node);
  setTimeout(() => {
    node.classList.add("leaving");
    node.addEventListener("animationend", () => node.remove(), { once: true });
  }, ms);
  return node;
}

/* -------------------------------------------------------------------------
   Inline alerts & buttons
   ------------------------------------------------------------------------- */

export function showAlert(node, message, variant = "error") {
  if (!node) return;
  node.className = `alert alert-${variant}`;
  node.textContent = message;
  node.hidden = false;
}

export function hideAlert(node) {
  if (node) node.hidden = true;
}

export function setLoading(button, loading, label) {
  if (!button) return;
  if (loading) {
    button.dataset.label = button.textContent;
    button.classList.add("is-loading");
    button.disabled = true;
  } else {
    button.classList.remove("is-loading");
    button.disabled = false;
    if (label ?? button.dataset.label) button.textContent = label ?? button.dataset.label;
  }
}

export function fieldError(input, message) {
  if (!input) return;
  const target = input.closest(".field")?.querySelector(".field-error");
  if (message) {
    input.setAttribute("aria-invalid", "true");
    if (target) {
      target.textContent = message;
      target.classList.add("show");
    }
  } else {
    input.removeAttribute("aria-invalid");
    if (target) target.classList.remove("show");
  }
}

export function clearFieldErrors(form) {
  $$(".field-error", form).forEach((n) => n.classList.remove("show"));
  $$("[aria-invalid]", form).forEach((n) => n.removeAttribute("aria-invalid"));
}

/* -------------------------------------------------------------------------
   Validation
   ------------------------------------------------------------------------- */

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function validateEmail(value) {
  if (!value?.trim()) return "Enter your email address.";
  if (!EMAIL_RE.test(value.trim())) return "That doesn't look like a valid email address.";
  return null;
}

/** Mirrors the server's rule in modules/backend/src/security.py. */
export function validatePassword(value) {
  if (!value) return "Enter a password.";
  if (value.length < 8) return "Password must be at least 8 characters.";
  if (value.length > 128) return "Password must be at most 128 characters.";
  if (!/[a-z]/.test(value)) return "Include at least one lowercase letter.";
  if (!/[A-Z]/.test(value)) return "Include at least one uppercase letter.";
  if (!/\d/.test(value)) return "Include at least one number.";
  return null;
}

export function passwordScore(value) {
  if (!value) return 0;
  let score = 0;
  if (value.length >= 8) score++;
  if (value.length >= 12) score++;
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
  if (/\d/.test(value) && /[^\w\s]/.test(value)) score++;
  return Math.min(score, 4);
}

/* -------------------------------------------------------------------------
   Theme
   ------------------------------------------------------------------------- */

const THEME_KEY = "shikshak.theme";

export function applyStoredTheme() {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored) document.documentElement.dataset.theme = stored;
  } catch {
    /* fall back to the OS preference */
  }
}

/** The theme actually in effect, whether chosen explicitly or inherited from the OS. */
export function effectiveTheme() {
  return (
    document.documentElement.dataset.theme ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
  );
}

export function toggleTheme() {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* not persisting the choice is acceptable */
  }
  return next;
}

applyStoredTheme();

/* -------------------------------------------------------------------------
   Auth guards
   ------------------------------------------------------------------------- */

/** Redirect to login unless signed in; returns the current user. */
export async function requireAuth() {
  if (!tokens.isSignedIn) {
    const next = window.location.pathname + window.location.search;
    window.location.replace(`/login.html?next=${encodeURIComponent(next)}`);
    return null;
  }
  try {
    const user = await api.me();
    tokens.saveUser(user);
    return user;
  } catch (error) {
    if (error.status === 401 || error.status === 403) {
      tokens.clear();
      window.location.replace("/login.html");
      return null;
    }
    // A network blip shouldn't sign the learner out; use the cached profile.
    return tokens.user;
  }
}

/** Send already-signed-in visitors away from auth pages. */
export function redirectIfSignedIn(destination = "/dashboard.html") {
  if (tokens.isSignedIn) {
    window.location.replace(destination);
    return true;
  }
  return false;
}

/* -------------------------------------------------------------------------
   Icons
   ------------------------------------------------------------------------- */

const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  book: '<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5z"/><path d="M4 17h16"/>',
  chart: '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>',
  settings:
    '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
  logout: '<path d="M15 4h4v16h-4"/><path d="M10 8l-4 4 4 4"/><path d="M6 12h10"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v13"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8"/>',
  play: '<path d="M6 4l14 8-14 8z" fill="currentColor" stroke="none"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/>',
  arrowLeft: '<path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/>',
  arrowRight: '<path d="M5 12h14"/><path d="M12 5l7 7-7 7"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  flame: '<path d="M12 22c4 0 7-2.7 7-6.5 0-4.5-4.5-6-4-11.5-3 1-6 4.6-6 8 0 1.2.4 2.2 1 3-1.2 0-2-1-2-2.5C6.5 15 7.6 22 12 22z"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
  alert: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
};

export function icon(name, size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${
    ICONS[name] || ""
  }</svg>`;
}

export const BRAND_MARK = `
<svg class="brand-mark" viewBox="0 0 32 32" fill="none" aria-hidden="true">
  <path d="M7 16C7 11.03 11.03 7 16 7" stroke="var(--indigo-600)" stroke-width="3" stroke-linecap="round"/>
  <path d="M25 16C25 20.97 20.97 25 16 25" stroke="var(--teal-600)" stroke-width="3" stroke-linecap="round"/>
  <circle cx="16" cy="16" r="3.5" fill="var(--indigo-600)"/>
</svg>`;

/* -------------------------------------------------------------------------
   App header + mobile nav
   ------------------------------------------------------------------------- */

const NAV_ITEMS = [
  { href: "/dashboard.html", label: "Dashboard", icon: "home" },
  { href: "/new-lesson.html", label: "New lesson", icon: "plus" },
  { href: "/lessons.html", label: "My lessons", icon: "book" },
  { href: "/analytics.html", label: "Progress", icon: "chart" },
];

export function mountHeader(user, current = "") {
  const host = $("#app-header");
  if (!host) return;

  const initials = user?.initials || "··";
  const color = user?.avatar_color || "var(--indigo-600)";

  host.className = "app-header";
  host.innerHTML = `
    <a class="brand" href="/dashboard.html">${BRAND_MARK}<span>Shikshak<span class="ai">AI</span></span></a>
    <nav class="app-nav" aria-label="Main">
      ${NAV_ITEMS.map(
        (item) =>
          `<a class="nav-link" href="${item.href}"${
            item.href === current ? ' aria-current="page"' : ""
          }>${item.label}</a>`
      ).join("")}
    </nav>
    <div class="header-actions">
      <button class="btn btn-ghost btn-icon" id="theme-toggle" type="button"
              title="Switch theme" aria-label="Switch colour theme">${icon(
                effectiveTheme() === "dark" ? "sun" : "moon",
                18
              )}</button>
      <div class="account-menu">
        <button class="account-trigger" id="account-trigger" type="button" aria-haspopup="menu" aria-expanded="false">
          <span class="avatar" style="background:${escapeHtml(color)}">${escapeHtml(initials)}</span>
          <span class="account-name">${escapeHtml(user?.full_name || "Account")}</span>
        </button>
        <div class="menu-panel" id="account-panel" role="menu" hidden>
          <div class="menu-header">
            <div style="font-weight:650;font-size:var(--text-sm)">${escapeHtml(user?.full_name || "")}</div>
            <div class="menu-email">${escapeHtml(user?.email || "")}</div>
          </div>
          <a class="menu-item" role="menuitem" href="/settings.html">${icon("settings", 17)} Account settings</a>
          <a class="menu-item" role="menuitem" href="/analytics.html">${icon("chart", 17)} Progress analytics</a>
          <div class="menu-divider"></div>
          <button class="menu-item danger" role="menuitem" type="button" id="logout-btn">${icon(
            "logout",
            17
          )} Sign out</button>
        </div>
      </div>
    </div>`;

  wireHeader();
  mountMobileNav(current);
}

// mountHeader can run more than once on a page (for example after saving a
// profile), so document-level listeners are attached only on the first mount
// and look the menu up fresh each time.
let documentListenersBound = false;

function closeAccountMenu() {
  const panel = $("#account-panel");
  const trigger = $("#account-trigger");
  if (panel && !panel.hidden) {
    panel.hidden = true;
    trigger?.setAttribute("aria-expanded", "false");
    return trigger;
  }
  return null;
}

function wireHeader() {
  const trigger = $("#account-trigger");
  const panel = $("#account-panel");

  trigger?.addEventListener("click", (event) => {
    event.stopPropagation();
    const open = panel.hidden;
    panel.hidden = !open;
    trigger.setAttribute("aria-expanded", String(open));
  });

  if (!documentListenersBound) {
    documentListenersBound = true;

    document.addEventListener("click", (event) => {
      const currentPanel = $("#account-panel");
      const currentTrigger = $("#account-trigger");
      if (
        currentPanel &&
        !currentPanel.hidden &&
        !currentPanel.contains(event.target) &&
        !currentTrigger?.contains(event.target)
      ) {
        closeAccountMenu();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeAccountMenu()?.focus();
    });
  }

  $("#theme-toggle")?.addEventListener("click", (event) => {
    const next = toggleTheme();
    event.currentTarget.innerHTML = icon(next === "dark" ? "sun" : "moon", 18);
  });

  $("#logout-btn")?.addEventListener("click", async () => {
    await api.logout();
    window.location.href = "/login.html";
  });
}

function mountMobileNav(current) {
  if ($(".mobile-nav")) return;
  const nav = el("nav", { class: "mobile-nav", "aria-label": "Main" });
  nav.innerHTML = NAV_ITEMS.map(
    (item) =>
      `<a href="${item.href}"${item.href === current ? ' aria-current="page"' : ""}>${icon(
        item.icon,
        21
      )}<span>${item.label}</span></a>`
  ).join("");
  document.body.append(nav);
  document.body.classList.add("has-mobile-nav");
}

/* -------------------------------------------------------------------------
   Misc
   ------------------------------------------------------------------------- */

export function emptyState(iconName, title, body, action) {
  const node = el("div", { class: "empty-state" });
  node.innerHTML = `${icon(iconName, 40)}<h3>${escapeHtml(title)}</h3><p>${escapeHtml(body)}</p>`;
  if (action) node.append(action);
  return node;
}

export function confirmDialog({ title, body, confirmLabel = "Confirm", danger = false }) {
  return new Promise((resolve) => {
    const backdrop = el("div", { class: "modal-backdrop" });
    backdrop.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <div class="card-body stack" style="--gap:var(--sp-4)">
          <h3 id="confirm-title">${escapeHtml(title)}</h3>
          <p class="muted" style="font-size:var(--text-sm)">${escapeHtml(body)}</p>
          <div class="row" style="justify-content:flex-end">
            <button class="btn btn-secondary" data-act="cancel" type="button">Cancel</button>
            <button class="btn ${danger ? "btn-danger" : "btn-primary"}" data-act="ok" type="button">${escapeHtml(
              confirmLabel
            )}</button>
          </div>
        </div>
      </div>`;

    const close = (result) => {
      backdrop.remove();
      document.removeEventListener("keydown", onKey);
      resolve(result);
    };
    const onKey = (event) => event.key === "Escape" && close(false);

    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) close(false);
      const act = event.target.closest("[data-act]")?.dataset.act;
      if (act === "cancel") close(false);
      if (act === "ok") close(true);
    });
    document.addEventListener("keydown", onKey);
    document.body.append(backdrop);
    $('[data-act="ok"]', backdrop).focus();
  });
}

/** Reveal a password field, toggling the button's icon. */
export function wirePasswordToggle(button, input) {
  button?.addEventListener("click", () => {
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    button.innerHTML = showing
      ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>'
      : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 3l18 18"/><path d="M10.6 10.6a3 3 0 0 0 4.2 4.2"/><path d="M9.4 5.2A9.7 9.7 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3 3.9M6.2 6.2A17 17 0 0 0 2 12s3.6 7 10 7c1.4 0 2.6-.3 3.8-.8"/></svg>';
  });
}
