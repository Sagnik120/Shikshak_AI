/** Login page: authenticate, store tokens, return to the intended page. */
import { api, tokens, ApiError } from "../api.js";
import {
  $, showAlert, hideAlert, setLoading, fieldError, clearFieldErrors,
  validateEmail, redirectIfSignedIn, wirePasswordToggle,
} from "../ui.js";

if (!redirectIfSignedIn()) {
  const params = new URLSearchParams(window.location.search);
  const form = $("#login-form");
  const alertBox = $("#form-alert");
  const submitBtn = $("#submit-btn");
  const emailInput = $("#email");
  const passwordInput = $("#password");

  wirePasswordToggle($("#toggle-password"), passwordInput);

  // Messages passed in by the pages that redirect here.
  if (params.get("reset") === "1") {
    showAlert(alertBox, "Password updated. Sign in with your new password.", "success");
  } else if (params.get("signedout") === "1") {
    showAlert(alertBox, "You've been signed out.", "info");
  } else if (params.get("next")) {
    showAlert(alertBox, "Please sign in to continue.", "info");
  }

  const prefill = params.get("email") || sessionStorage.getItem("shikshak.pendingEmail");
  if (prefill) {
    emailInput.value = prefill;
    passwordInput.focus();
  }

  form.addEventListener("input", (event) => {
    if (event.target.matches(".input")) fieldError(event.target, null);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlert(alertBox);
    clearFieldErrors(form);

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    const emailError = validateEmail(email);
    if (emailError) {
      fieldError(emailInput, emailError);
      emailInput.focus();
      return;
    }
    if (!password) {
      fieldError(passwordInput, "Enter your password.");
      passwordInput.focus();
      return;
    }

    setLoading(submitBtn, true);
    try {
      const session = await api.login(email, password);
      tokens.save(session);
      sessionStorage.removeItem("shikshak.pendingEmail");

      // Only follow same-origin paths, so ?next= can't be used to send
      // a freshly signed-in learner to another site.
      const next = params.get("next");
      const safeNext = next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard.html";
      window.location.href = safeNext;
    } catch (error) {
      setLoading(submitBtn, false, "Sign in");

      // An unverified account should go finish verifying, not stare at an error.
      if (error instanceof ApiError && error.status === 403 && /verify/i.test(error.message)) {
        sessionStorage.setItem("shikshak.pendingEmail", email);
        showAlert(alertBox, `${error.message} Taking you there now…`, "warning");
        try {
          await api.resendOtp(email, "verify_email");
          sessionStorage.removeItem("shikshak.devOtp");
        } catch {
          /* the verify page offers a resend button anyway */
        }
        setTimeout(() => (window.location.href = `/verify.html?email=${encodeURIComponent(email)}`), 1400);
        return;
      }

      showAlert(alertBox, error.message, "error");
      passwordInput.select();
    }
  });
}
