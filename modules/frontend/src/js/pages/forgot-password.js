/** Request a password reset code, then move to the reset page. */
import { api } from "../api.js";
import {
  $, showAlert, hideAlert, setLoading, fieldError, validateEmail, redirectIfSignedIn,
} from "../ui.js";

if (!redirectIfSignedIn()) {
  const form = $("#forgot-form");
  const alertBox = $("#form-alert");
  const submitBtn = $("#submit-btn");
  const emailInput = $("#email");

  emailInput.value = sessionStorage.getItem("shikshak.pendingEmail") || "";

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlert(alertBox);
    fieldError(emailInput, null);

    const email = emailInput.value.trim();
    const error = validateEmail(email);
    if (error) {
      fieldError(emailInput, error);
      emailInput.focus();
      return;
    }

    setLoading(submitBtn, true);
    try {
      const response = await api.forgotPassword(email);
      sessionStorage.setItem("shikshak.pendingEmail", email);
      sessionStorage.removeItem("shikshak.devOtp");

      showAlert(alertBox, `${response.message} Taking you to the next step…`, "success");
      setTimeout(
        () => (window.location.href = `/reset-password.html?email=${encodeURIComponent(email)}`),
        1200
      );
    } catch (err) {
      showAlert(alertBox, err.message, "error");
      setLoading(submitBtn, false, "Send reset code");
    }
  });
}
