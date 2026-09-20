/** Consume a reset code and set a new password. */
import { api } from "../api.js";
import {
  $, showAlert, hideAlert, setLoading, fieldError, clearFieldErrors,
  validatePassword, passwordScore, redirectIfSignedIn, wirePasswordToggle, toast,
} from "../ui.js";
import { wireOtpInputs, startCooldown } from "../otp.js";

if (!redirectIfSignedIn()) {
  const params = new URLSearchParams(window.location.search);
  const email = params.get("email") || sessionStorage.getItem("shikshak.pendingEmail") || "";

  const form = $("#reset-form");
  const alertBox = $("#form-alert");
  const devNotice = $("#dev-notice");
  const submitBtn = $("#submit-btn");
  const passwordInput = $("#password");
  const confirmInput = $("#confirm");
  const strength = $("#strength");
  const resendBtn = $("#resend-btn");
  const resendTimer = $("#resend-timer");

  if (!email) {
    window.location.replace("/forgot-password.html");
  } else {
    $("#target-email").textContent = email;
    wirePasswordToggle($("#toggle-password"), passwordInput);

    const devOtp = sessionStorage.getItem("shikshak.devOtp");
    if (devOtp && devNotice) {
      devNotice.textContent = `Your reset code is: ${devOtp}`;
      devNotice.hidden = false;
    }

    const otp = wireOtpInputs($("#otp-inputs"), () => passwordInput.focus());
    otp.focus();
    startCooldown(resendBtn, resendTimer, 60);

    passwordInput.addEventListener("input", () => {
      strength.dataset.score = String(passwordScore(passwordInput.value));
    });
    form.addEventListener("input", (event) => {
      if (event.target.matches(".input")) fieldError(event.target, null);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideAlert(alertBox);
      clearFieldErrors(form);

      const code = otp.value;
      if (code.length !== 6) {
        showAlert(alertBox, "Enter all six digits of your reset code.", "error");
        otp.focus();
        return;
      }

      const passwordError = validatePassword(passwordInput.value);
      if (passwordError) {
        fieldError(passwordInput, passwordError);
        passwordInput.focus();
        return;
      }
      if (passwordInput.value !== confirmInput.value) {
        fieldError(confirmInput, "The two passwords don't match.");
        confirmInput.focus();
        return;
      }

      setLoading(submitBtn, true);
      try {
        await api.resetPassword(email, code, passwordInput.value);
        sessionStorage.removeItem("shikshak.devOtp");
        window.location.href = `/login.html?reset=1&email=${encodeURIComponent(email)}`;
      } catch (error) {
        showAlert(alertBox, error.message, "error");
        setLoading(submitBtn, false, "Update password");
        if (/code/i.test(error.message)) otp.clear();
      }
    });

    resendBtn.addEventListener("click", async () => {
      hideAlert(alertBox);
      setLoading(resendBtn, true);
      try {
        const response = await api.resendOtp(email, "reset_password");
        toast("A new reset code is on its way.", "success");
        if (response.dev_otp && devNotice) {
          devNotice.textContent = `Your reset code is: ${response.dev_otp}`;
          devNotice.hidden = false;
        }
        otp.clear();
        startCooldown(resendBtn, resendTimer, 60);
      } catch (error) {
        showAlert(alertBox, error.message, "error");
      } finally {
        setLoading(resendBtn, false, "Resend code");
      }
    });
  }
}
