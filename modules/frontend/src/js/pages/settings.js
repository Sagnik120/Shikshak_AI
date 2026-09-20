/** Account settings: profile, learning preferences, password, devices, deletion. */
import { api, tokens } from "../api.js";
import {
  $, $$, el, clear, escapeHtml, icon, toast, requireAuth, mountHeader,
  showAlert, hideAlert, setLoading, fieldError, clearFieldErrors,
  validatePassword, passwordScore, wirePasswordToggle, confirmDialog,
  formatRelative, formatDate,
} from "../ui.js";

const user = await requireAuth();
if (user) {
  mountHeader(user, "/settings.html");

  const AVATAR_COLOURS = [
    "#2A3FA0", "#0FA3A3", "#0F9D58", "#D97A06",
    "#D92D4E", "#7C3AED", "#0B7E7E", "#334155",
  ];

  let profile = { ...user };

  /* --- tabs ------------------------------------------------------------ */

  const tabs = $$(".settings-nav button");

  function showPanel(name) {
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.panel === name)));
    $$(".settings-panel").forEach((p) => (p.hidden = p.id !== `panel-${name}`));
    // Keep the section in the URL so a reload or back-button lands in place.
    window.history.replaceState({}, "", `/settings.html#${name}`);
    if (name === "devices") loadSessions();
  }

  tabs.forEach((tab) => tab.addEventListener("click", () => showPanel(tab.dataset.panel)));

  const initialTab = window.location.hash.slice(1);
  showPanel(tabs.some((t) => t.dataset.panel === initialTab) ? initialTab : "profile");

  /* --- profile --------------------------------------------------------- */

  const avatarPreview = $("#avatar-preview");

  function paintAvatar() {
    avatarPreview.textContent = profile.initials || "··";
    avatarPreview.style.background = profile.avatar_color;
  }

  const swatches = $("#swatches");
  AVATAR_COLOURS.forEach((colour) => {
    const swatch = el("button", {
      class: "swatch",
      type: "button",
      style: `background:${colour}`,
      "aria-pressed": String(colour.toLowerCase() === profile.avatar_color.toLowerCase()),
      "aria-label": `Use ${colour}`,
    });
    swatch.addEventListener("click", async () => {
      $$(".swatch", swatches).forEach((s) => s.setAttribute("aria-pressed", String(s === swatch)));
      profile.avatar_color = colour;
      paintAvatar();
      try {
        const updated = await api.updateProfile({ avatar_color: colour });
        profile = updated;
        tokens.saveUser(updated);
        mountHeader(updated, "/settings.html");
        // Re-mounting the header rebinds its listeners, so the tabs stay live.
        toast("Avatar colour updated.", "success");
      } catch (error) {
        toast(error.message, "error");
      }
    });
    swatches.append(swatch);
  });

  $("#full_name").value = profile.full_name;
  $("#email-display").value = profile.email;
  $("#grade").value = profile.grade || "";
  $("#board").value = profile.board || "";
  paintAvatar();

  $("#profile-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const alertBox = $("#profile-alert");
    const button = $("#profile-save");
    hideAlert(alertBox);
    clearFieldErrors($("#profile-form"));

    const fullName = $("#full_name").value.trim();
    if (fullName.length < 2) {
      fieldError($("#full_name"), "Enter your full name.");
      return;
    }

    setLoading(button, true);
    try {
      const updated = await api.updateProfile({
        full_name: fullName,
        grade: $("#grade").value || null,
        board: $("#board").value || null,
      });
      profile = updated;
      tokens.saveUser(updated);
      paintAvatar();
      mountHeader(updated, "/settings.html");
      showAlert(alertBox, "Profile saved.", "success");
    } catch (error) {
      showAlert(alertBox, error.message, "error");
    } finally {
      setLoading(button, false, "Save profile");
    }
  });

  /* --- learning preferences -------------------------------------------- */

  let level = profile.preferred_level;
  $$("#level-group button").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.value === level))
  );
  $("#level-group").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-value]");
    if (!button) return;
    level = button.dataset.value;
    $$("#level-group button").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
  });

  $("#preferred_language").value = profile.preferred_language;
  $("#preferred_style").value = profile.preferred_style || "visual";
  $("#default_time_budget_min").value = String(profile.default_time_budget_min);

  $("#learning-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const alertBox = $("#learning-alert");
    const button = $("#learning-save");
    hideAlert(alertBox);
    setLoading(button, true);

    try {
      const updated = await api.updateProfile({
        preferred_level: level,
        preferred_language: $("#preferred_language").value,
        preferred_style: $("#preferred_style").value,
        default_time_budget_min: Number($("#default_time_budget_min").value),
      });
      profile = updated;
      tokens.saveUser(updated);
      showAlert(alertBox, "Preferences saved — new lessons will use these.", "success");
    } catch (error) {
      showAlert(alertBox, error.message, "error");
    } finally {
      setLoading(button, false, "Save preferences");
    }
  });

  /* --- password -------------------------------------------------------- */

  const newPassword = $("#new_password");
  wirePasswordToggle($("#toggle-password"), newPassword);
  newPassword.addEventListener("input", () => {
    $("#strength").dataset.score = String(passwordScore(newPassword.value));
  });

  $("#password-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = $("#password-form");
    const alertBox = $("#password-alert");
    const button = $("#password-save");
    hideAlert(alertBox);
    clearFieldErrors(form);

    const current = $("#current_password").value;
    const next = newPassword.value;
    const confirm = $("#confirm_password").value;

    if (!current) {
      fieldError($("#current_password"), "Enter your current password.");
      return;
    }
    const strengthError = validatePassword(next);
    if (strengthError) {
      fieldError(newPassword, strengthError);
      return;
    }
    if (next !== confirm) {
      fieldError($("#confirm_password"), "The two passwords don't match.");
      return;
    }

    setLoading(button, true);
    try {
      await api.changePassword(current, next);
      showAlert(alertBox, "Password changed. Signing you out…", "success");
      tokens.clear();
      setTimeout(() => (window.location.href = "/login.html?signedout=1"), 1600);
    } catch (error) {
      showAlert(alertBox, error.message, "error");
      setLoading(button, false, "Change password");
    }
  });

  /* --- devices --------------------------------------------------------- */

  async function loadSessions() {
    const host = $("#sessions-list");
    try {
      const sessions = await api.listSessions();
      clear(host);

      if (!sessions.length) {
        host.innerHTML = '<p class="subtle">No active sessions.</p>';
        return;
      }

      sessions.forEach((session) => {
        const item = el("div", { class: "session-item" });
        item.innerHTML = `
          <span class="doc-icon">${icon("user", 18)}</span>
          <span class="grow">
            <span style="font-weight:600;font-size:var(--text-sm)">
              ${escapeHtml(describeAgent(session.user_agent))}
              ${session.current ? '<span class="badge badge-green" style="margin-left:6px">This device</span>' : ""}
            </span>
            <span class="subtle" style="display:block;font-size:11px">
              ${escapeHtml(session.ip_address || "Unknown IP")} ·
              signed in ${escapeHtml(formatRelative(session.created_at))} ·
              expires ${escapeHtml(formatDate(session.expires_at))}
            </span>
          </span>
          ${
            session.current
              ? ""
              : `<button class="btn btn-ghost btn-sm" data-revoke="${escapeHtml(session.id)}">Sign out</button>`
          }`;

        $("[data-revoke]", item)?.addEventListener("click", async (event) => {
          const button = event.currentTarget;
          setLoading(button, true);
          try {
            await api.revokeSession(session.id);
            toast("That device has been signed out.");
            loadSessions();
          } catch (error) {
            toast(error.message, "error");
            setLoading(button, false, "Sign out");
          }
        });

        host.append(item);
      });
    } catch (error) {
      clear(host).append(el("p", { class: "subtle" }, error.message));
    }
  }

  /** Turn a user-agent string into something a learner can recognise. */
  function describeAgent(agent) {
    if (!agent) return "Unknown device";
    const browser =
      /Edg\//.test(agent) ? "Edge"
      : /OPR\//.test(agent) ? "Opera"
      : /Chrome\//.test(agent) ? "Chrome"
      : /Firefox\//.test(agent) ? "Firefox"
      : /Safari\//.test(agent) ? "Safari"
      : "Browser";
    const platform =
      /iPhone|iPad/.test(agent) ? "iOS"
      : /Android/.test(agent) ? "Android"
      : /Mac OS X/.test(agent) ? "macOS"
      : /Windows/.test(agent) ? "Windows"
      : /Linux/.test(agent) ? "Linux"
      : "";
    return platform ? `${browser} on ${platform}` : browser;
  }

  $("#revoke-all").addEventListener("click", async () => {
    const ok = await confirmDialog({
      title: "Sign out everywhere?",
      body: "Every device, including this one, will be signed out.",
      confirmLabel: "Sign out everywhere",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.revokeAllSessions();
      tokens.clear();
      window.location.href = "/login.html?signedout=1";
    } catch (error) {
      toast(error.message, "error");
    }
  });

  /* --- delete account --------------------------------------------------- */

  $("#delete-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const alertBox = $("#delete-alert");
    const button = $("#delete-save");
    hideAlert(alertBox);

    const password = $("#delete_password").value;
    if (!password) {
      showAlert(alertBox, "Enter your password to confirm.", "error");
      return;
    }

    const ok = await confirmDialog({
      title: "Delete your account permanently?",
      body: "All your lessons, answers, uploaded material and videos will be erased. This cannot be undone.",
      confirmLabel: "Yes, delete everything",
      danger: true,
    });
    if (!ok) return;

    setLoading(button, true);
    try {
      await api.deleteAccount(password);
      tokens.clear();
      window.location.href = "/?deleted=1";
    } catch (error) {
      showAlert(alertBox, error.message, "error");
      setLoading(button, false, "Permanently delete my account");
    }
  });
}
