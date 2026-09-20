/** Signup page: validate, register, then hand off to OTP verification. */
import { api, ApiError } from "../api.js";
import {
  $, showAlert, hideAlert, setLoading, fieldError, clearFieldErrors,
  validateEmail, validatePassword, passwordScore, redirectIfSignedIn,
  wirePasswordToggle, toast,
} from "../ui.js";

if (!redirectIfSignedIn()) {
  const form = $("#signup-form");
  const alertBox = $("#form-alert");
  const submitBtn = $("#submit-btn");
  const passwordInput = $("#password");
  const strength = $("#strength");

  wirePasswordToggle($("#toggle-password"), passwordInput);

  passwordInput.addEventListener("input", () => {
    strength.dataset.score = String(passwordScore(passwordInput.value));
  });

  // Clear a field's error as soon as the learner starts fixing it.
  form.addEventListener("input", (event) => {
    if (event.target.matches(".input, .select")) fieldError(event.target, null);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideAlert(alertBox);
    clearFieldErrors(form);

    const fullName = $("#full_name").value.trim();
    const email = $("#email").value.trim();
    const password = passwordInput.value;

    let firstInvalid = null;
    if (fullName.length < 2) {
      fieldError($("#full_name"), "Enter your full name.");
      firstInvalid ??= $("#full_name");
    }
    const emailError = validateEmail(email);
    if (emailError) {
      fieldError($("#email"), emailError);
      firstInvalid ??= $("#email");
    }
    const passwordError = validatePassword(password);
    if (passwordError) {
      fieldError(passwordInput, passwordError);
      firstInvalid ??= passwordInput;
    }
    if (!$("#terms").checked) {
      showAlert(alertBox, "Please accept the storage notice to continue.", "warning");
      firstInvalid ??= $("#terms");
    }

    if (firstInvalid) {
      firstInvalid.focus();
      return;
    }

    setLoading(submitBtn, true);
    try {
      const response = await api.signup({
        full_name: fullName,
        email,
        password,
        grade: $("#grade").value || null,
        board: $("#board").value || null,
        preferred_language: $("#preferred_language").value,
      });

      // Carry the address forward so the verify page doesn't ask for it again.
      sessionStorage.setItem("shikshak.pendingEmail", email);
      if (response.dev_otp) {
        sessionStorage.setItem("shikshak.devOtp", response.dev_otp);
      }
      window.location.href = `/verify.html?email=${encodeURIComponent(email)}`;
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        showAlert(alertBox, error.message, "error");
        $("#email").focus();
      } else {
        showAlert(alertBox, error.message || "Could not create your account.", "error");
      }
      setLoading(submitBtn, false, "Create account");
    }
  });
}
